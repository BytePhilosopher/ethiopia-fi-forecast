"""Capture full-page screenshots of the running dashboard for the README and final report.

Starts Streamlit headlessly, drives the sidebar with Playwright, saves one PNG per page to
reports/figures/dashboard/, then stitches them into dashboard_demo.gif for the README.
Run: python scripts/capture_dashboard.py
"""
import subprocess, sys, time, socket, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures" / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8601
GIF_WIDTH = 1200        # README-friendly width
GIF_MS_PER_FRAME = 2500
# page -> a text marker unique to that page's body (confirms the rerun finished)
PAGES = {
    "Overview": "P2P / ATM crossover",
    "Trends": "Channel comparison",
    "Forecasts": "Key projected milestones",
    "Inclusion Projections": "Progress toward 60%",
    "Explainability": "What makes an event impactful?",
}
# Streamlit scrolls inside its own container, so Playwright's full_page stops at the
# viewport. For pages whose content runs past one screen, take an extra shot named
# "<page>_2": page -> (marker rendered *after* the below-fold chart, scroll target).
# Waiting on a marker that follows the chart is what guarantees it has actually drawn.
EXTRA_SCROLL = {
    "Explainability": ("Concerning pattern surfaced", "What makes an event impactful?"),
}


def _chromium_executable():
    """Prefer the headless shell; fall back to the full Chrome-for-Testing build."""
    cand = glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"))
    return cand[0] if cand else None


def _wait_port(port, timeout=40):
    for _ in range(timeout * 2):
        with socket.socket() as s:
            if s.connect_ex(("localhost", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def build_gif(names):
    """Stitch the captured PNGs into a looping GIF for the README."""
    try:
        from PIL import Image
    except ImportError:
        print("gif skipped: Pillow not installed")
        return
    frames = []
    for n in names:
        p = OUT / f"dash_{n}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        frames.append(im.resize((GIF_WIDTH, int(im.height * GIF_WIDTH / im.width)),
                                Image.LANCZOS))
    if not frames:
        print("gif skipped: no frames")
        return
    # pad to a common canvas so the GIF doesn't jitter between differently-tall pages
    h = max(f.height for f in frames)
    canvas = []
    for f in frames:
        c = Image.new("RGB", (GIF_WIDTH, h), "white")
        c.paste(f, (0, 0))
        canvas.append(c)
    out = OUT / "dashboard_demo.gif"
    canvas[0].save(out, save_all=True, append_images=canvas[1:],
                   duration=GIF_MS_PER_FRAME, loop=0, optimize=True)
    print(f"saved {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.2f} MB, "
          f"{len(canvas)} frames)")


def main():
    captured = []
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
         "--server.headless", "true", "--server.port", str(PORT),
         "--browser.gatherUsageStats", "false"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert _wait_port(PORT), "streamlit did not start"
        time.sleep(4)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = _chromium_executable()
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 1000},
                                    device_scale_factor=2)
            page.goto(f"http://localhost:{PORT}", wait_until="networkidle")
            time.sleep(3)
            for name, marker in PAGES.items():
                try:
                    page.get_by_text(name, exact=True).first.click()
                    # wait for this page's unique marker to appear, then for Plotly to draw
                    page.get_by_text(marker, exact=False).first.wait_for(timeout=30000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector(".stSpinner", state="detached", timeout=5000)
                except Exception as e:
                    print("nav warn", name, e)
                time.sleep(3)  # let Plotly finish animating
                slug = name.lower().replace(" ", "_")
                fn = OUT / f"dash_{slug}.png"
                page.screenshot(path=str(fn), full_page=True)
                print("saved", fn.relative_to(ROOT))
                captured.append(slug)

                if name in EXTRA_SCROLL:
                    after_marker, scroll_marker = EXTRA_SCROLL[name]
                    try:
                        # the SHAP surrogate takes several seconds to fit on a cold cache
                        page.get_by_text(after_marker, exact=False).first.wait_for(timeout=120000)
                        page.wait_for_load_state("networkidle")
                        page.get_by_text(scroll_marker, exact=False).first.scroll_into_view_if_needed()
                        time.sleep(4)
                        fn2 = OUT / f"dash_{slug}_2.png"
                        page.screenshot(path=str(fn2), full_page=True)
                        print("saved", fn2.relative_to(ROOT))
                        captured.append(f"{slug}_2")
                    except Exception as e:
                        print("scroll warn", name, e)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    build_gif(captured)


if __name__ == "__main__":
    main()
