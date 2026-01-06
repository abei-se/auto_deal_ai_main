from playwright.sync_api import sync_playwright
from willhaben_url import extract_sfid, BASE

def get_fresh_sfid(timeout_ms: int = 20000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=timeout_ms)

        # manchmal wird umgeleitet oder Parameter werden nachgeladen
        page.wait_for_timeout(1000)

        sfid = extract_sfid(page.url)
        browser.close()

        if not sfid:
            raise RuntimeError(f"Konnte sfId nicht aus URL lesen: {page.url}")
        return sfid
