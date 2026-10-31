"""Run against a running local server: python scripts/browser_smoke.py speech.mp4.
Requires Playwright and Chromium. Pass --chromium for a system browser binary.
"""

import argparse

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mp4")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--chromium", default=None)
    parser.add_argument("--speakers", default="0")
    parser.add_argument("--radio-speaker", type=int)
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, headless=True)
        page = browser.new_page()
        errors, external = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "request",
            lambda r: external.append(r.url) if not r.url.startswith(args.url + "/") else None,
        )
        page.goto(args.url)
        page.wait_for_function('() => !document.getElementById("start").disabled')
        page.locator("#file").set_input_files(args.mp4)
        page.select_option("#speakers", args.speakers)
        page.locator("#start").click()
        page.locator("#result").wait_for(state="visible", timeout=180000)
        assert page.locator(".track").count() > 0
        audio = page.locator(".track audio").first
        audio.evaluate("(a) => a.load()")
        page.wait_for_function('() => document.querySelector(".track audio").duration > 0')
        if args.radio_speaker:
            page.locator(f'.radio-speaker[data-speaker="{args.radio_speaker}"]').check()
            page.select_option("#mix-mode", "remove_radio")
            page.locator("#mix-button").click()
            page.locator("#result").wait_for(state="hidden")
            page.locator("#result").wait_for(state="visible", timeout=180000)
            assert "Nieuwe mix gereed" in page.locator("#mix-note").inner_text()
            link = page.get_by_role("link", name="Download deze mix voor Premiere")
            assert link.is_visible()
            assert page.locator('audio[src$="removed.wav"]').count() == 1
            print("Radio choice → new mix → Premiere download: OK")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        assert not external, external
        if args.screenshot:
            page.screenshot(path=args.screenshot, full_page=True)
        print(page.locator("#summary").inner_text())
        print("Browser upload, audio decoding, mobile layout and local-only requests: OK")
        browser.close()


if __name__ == "__main__":
    main()
