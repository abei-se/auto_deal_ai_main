import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re

from db import insert_car


SEARCH_URL = (
    "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?sfId=dfa343fc-cab3-4c8c-8b6e-3eb5fc9e0002&isNavigation=true&CAR_TYPE=6&CAR_MODEL/MAKE=1003&CAR_MODEL/MODEL=1024&CAR_MODEL/MODEL=2065&rows=30&page=1&YEAR_MODEL_FROM=2018&MILEAGE_TO=150000&PRICE_TO=30000"
)

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

                            text = text.lower()

                            # bevorzugt PS
                            if "ps" in text:
                                m = re.search(r"(\d+)\s*ps", text)
                                if m:
                                    return int(m.group(1))

                            # fallback kW → PS
                            if "kw" in text:
                                m = re.search(r"(\d+)\s*kw", text)
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
    # willhaben URLs end often with numeric ID
    m = re.search(r"-([0-9]{6,})$", url)
    if m:
        return m.group(1)
    m2 = re.search(r"/([0-9]{6,})$", url)
    return m2.group(1) if m2 else url


def accept_cookies(page, timeout_ms=6000):
    """
    Robust cookie accept:
    - tries main document buttons
    - tries inside iframes
    - supports multiple German labels and common CMP selectors
    """
    candidates = [
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Akzeptieren")',
        'button:has-text("Zustimmen")',
        'button:has-text("Einverstanden")',
        'button:has-text("Alles akzeptieren")',
        '[data-testid*="accept"]',
        '[id*="accept"]',
        '[class*="accept"]',
        'button[mode="primary"]',
        'button:has-text("OK")',
    ]

    def try_click_in_context(ctx, label):
        for sel in candidates:
            loc = ctx.locator(sel).first
            try:
                if loc.is_visible(timeout=800):
                    loc.click(timeout=1500)
                    page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False

    # 1) try on main page
    try:
        page.wait_for_timeout(800)
        if try_click_in_context(page, "main"):
            return True
    except Exception:
        pass

    # 2) try in frames
    try:
        for fr in page.frames:
            try:
                if fr == page.main_frame:
                    continue
                if try_click_in_context(fr, "frame"):
                    return True
            except Exception:
                continue
    except Exception:
        pass

    # 3) last attempt: search by role with common texts (main + frames)
    role_texts = ["Alle akzeptieren", "Akzeptieren", "Zustimmen", "OK"]
    for txt in role_texts:
        try:
            btn = page.get_by_role("button", name=txt).first
            if btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(500)
                return True
        except Exception:
            pass

    # try inside frames with role
    try:
        for fr in page.frames:
            for txt in role_texts:
                try:
                    btn = fr.get_by_role("button", name=txt).first
                    if btn.is_visible(timeout=800):
                        btn.click(timeout=1500)
                        page.wait_for_timeout(500)
                        return True
                except Exception:
                    continue
    except Exception:
        pass

    return False


def scroll_until_all_loaded(page, max_rounds=30):
    last_count = 0
    stable_rounds = 0

    for i in range(max_rounds):
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1100)

        links = page.query_selector_all('a[href^="/iad/gebrauchtwagen/d/auto/"]')
        current_count = len({el.get_attribute("href") for el in links if el.get_attribute("href")})

        print(f"Scroll {i + 1}: {current_count} Inserate")

        if current_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        # if count is stable for 2 rounds, stop
        if stable_rounds >= 2:
            break

        last_count = current_count


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent=REAL_UA,
            locale="de-AT",
            timezone_id="Europe/Vienna",
            viewport={"width": 1280, "height": 800}
        )

        page = context.new_page()

        # 1) Home
        page.goto("https://www.willhaben.at", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        clicked = accept_cookies(page)
        print("Cookie Accept (home):", "ok" if clicked else "nicht gefunden/ignoriert")
        page.wait_for_timeout(1200)

        # 2) Search
        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        clicked = accept_cookies(page)
        print("Cookie Accept (search):", "ok" if clicked else "nicht gefunden/ignoriert")
        page.wait_for_timeout(1200)

        all_links = set()
        page_number = 1

        while True:
            print(f"\n📄 Seite {page_number}")

            # aktuelle Seite vollständig scrollen
            scroll_until_all_loaded(page)

            # Inserate dieser Seite sammeln
            link_elements = page.query_selector_all(
                'a[href^="/iad/gebrauchtwagen/d/auto/"]'
            )

            for el in link_elements:
                href = el.get_attribute("href")
                if href:
                    all_links.add("https://www.willhaben.at" + href)

            print("Gesammelte Inserate gesamt:", len(all_links))

            next_page = page_number + 1

            next_btn = page.query_selector(
                f'a[aria-label="Zur Seite {next_page}"]'
            )

            if not next_btn:
                print("➡️ Keine weitere Seite gefunden")
                break

            print(f"➡️ Wechsle zu Seite {next_page}")
            next_btn.click()
            page.wait_for_timeout(4000)
            page_number += 1


        # nach dem Loop
        ad_links = list(all_links)


        for idx, url in enumerate(ad_links, start=1):
            print(f"➡️ Inserat {idx}/{len(ad_links)}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)

                # Sometimes banner can re-appear on detail pages
                accept_cookies(page)
                page.wait_for_timeout(700)

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


                

                # simple brand/model guess from title
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
                print("⚠️ Timeout:", e)
                continue
            except Exception as e:
                print("⚠️ Fehler:", e)
                continue

        print("✅ Alle Inserate gespeichert")
        page.pause()


if __name__ == "__main__":
    run()
