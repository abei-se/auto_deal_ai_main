import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from db import insert_car

REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

def parse_int(text):
    if not text:
        return None
    cleaned = (
        text.replace("€", "")
            .replace("km", "")
            .replace(".", "")
            .replace(" ", "")
            .replace("\u00a0", "")
            .strip()
    )
    digits = re.sub(r"[^\d]", "", cleaned)
    return int(digits) if digits else None

def parse_power_ps(text):
    if not text:
        return None
    t = text.lower()
    if "ps" in t:
        m = re.search(r"(\d+)\s*ps", t)
        return int(m.group(1)) if m else None
    if "kw" in t:
        m = re.search(r"(\d+)\s*kw", t)
        if m:
            kw = int(m.group(1))
            return int(kw * 1.35962)
    return None

def get_attribute(items, keyword):
    keyword = keyword.lower()
    for item in items:
        title = item.query_selector('[data-testid="attribute-title"]')
        value = item.query_selector('[data-testid="attribute-value"]')
        if not title or not value:
            continue
        if keyword in title.inner_text().strip().lower():
            return value.inner_text().strip()
    return None

def extract_external_id(url):
    m = re.search(r"-([0-9]{6,})/?$", url)
    if m:
        return m.group(1)
    m2 = re.search(r"/([0-9]{6,})/?$", url)
    return m2.group(1) if m2 else url

def accept_cookies(page):
    candidates = [
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Akzeptieren")',
        'button:has-text("Zustimmen")',
        'button:has-text("Einverstanden")',
        'button:has-text("Alles akzeptieren")',
        'button:has-text("OK")',
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                loc.click(timeout=1500)
                page.wait_for_timeout(500)
                return True
        except Exception:
            continue
    return False

def scroll_until_all_loaded(page, log, max_rounds=30):
    last_count = 0
    stable_rounds = 0

    for i in range(max_rounds):
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(900)

        links = page.query_selector_all('a[href^="/iad/gebrauchtwagen/d/auto/"]')
        current_count = len({el.get_attribute("href") for el in links if el.get_attribute("href")})
        log(f"Scroll {i + 1}: {current_count} Inserate")

        if current_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= 2:
            break

        last_count = current_count

def run_scrape(start_url: str, log_cb=print, headless: bool = False):
    def log(msg: str):
        try:
            log_cb(str(msg))
        except Exception:
            try:
                print(str(msg))
            except Exception:
                pass

    log(f"run_scrape gestartet: {start_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=REAL_UA,
            locale="de-AT",
            timezone_id="Europe/Vienna",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        page.goto("https://www.willhaben.at", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        clicked = accept_cookies(page)
        log(f"Cookie Accept (home): {'ok' if clicked else 'nicht gefunden/ignoriert'}")

        page.goto(start_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        clicked = accept_cookies(page)
        log(f"Cookie Accept (search): {'ok' if clicked else 'nicht gefunden/ignoriert'}")

        all_links = set()
        page_number = 1

        while True:
            log(f"Seite {page_number}")
            scroll_until_all_loaded(page, log)

            link_elements = page.query_selector_all('a[href^="/iad/gebrauchtwagen/d/auto/"]')
            for el in link_elements:
                href = el.get_attribute("href")
                if href:
                    all_links.add("https://www.willhaben.at" + href)

            log(f"Gesammelte Inserate gesamt: {len(all_links)}")

            next_page = page_number + 1
            next_btn = page.query_selector(f'a[aria-label="Zur Seite {next_page}"]')
            if not next_btn:
                log("Keine weitere Seite gefunden")
                break

            log(f"Wechsle zu Seite {next_page}")
            next_btn.click()
            page.wait_for_timeout(3000)
            page_number += 1

        ad_links = list(all_links)

        for idx, url in enumerate(ad_links, start=1):
            log(f"Inserat {idx}/{len(ad_links)}: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1200)
                accept_cookies(page)

                title_el = page.query_selector("h1")
                title = title_el.inner_text().strip() if title_el else None

                price_el = page.query_selector('span[data-testid^="contact-box-price-box-price-value"]')
                price = parse_int(price_el.inner_text()) if price_el else None

                items = page.query_selector_all('li[data-testid="attribute-item"]')
                km_raw = get_attribute(items, "kilometer")
                year_raw = get_attribute(items, "erstzulassung")
                power_raw = get_attribute(items, "leistung")

                km = parse_int(km_raw)
                year = int(year_raw.split("/")[-1]) if year_raw and "/" in year_raw else None
                power_ps = parse_power_ps(power_raw)

                brand = None
                model = None
                if title:
                    parts = title.split()
                    if len(parts) >= 1:
                        brand = parts[0]
                    if len(parts) >= 2:
                        model = parts[1]

                car = {
                    "platform": "willhaben",
                    "external_id": extract_external_id(url),
                    "title": title,
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "km": km,
                    "price": price,
                    "location": None,
                    "url": url,
                    "power_ps": power_ps,
                }

                insert_car(car)

            except PlaywrightTimeoutError as e:
                log(f"Timeout: {e}")
            except Exception as e:
                log(f"Fehler: {e}")

        log("Alle Inserate gespeichert")
        try:
            browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    from config import WILLHABEN_SFID
    from willhaben_url import build_search_url

    url = build_search_url(sfId=WILLHABEN_SFID, rows=30, page=1)
    run_scrape(url, headless=False)
