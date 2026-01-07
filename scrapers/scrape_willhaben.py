import sys
import os
import re
from db import insert_car, car_exists

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from db import insert_car

MAX_WORKERS = 4
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

def get_attr_any(items, keywords):
    for kw in keywords:
        v = get_attribute(items, kw)
        if v:
            return v
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

def scroll_until_all_loaded(page, log, max_rounds=7):
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

        from queue import Queue
        import threading

        def detail_worker(worker_id, context, queue, log):
            page = context.new_page()

            while True:
                url = queue.get()
                if url is None:
                    break

                try:
                    log(f"[W{worker_id}] Öffne {url}")

                    page.goto(url, wait_until="commit", timeout=30000)
                    page.wait_for_timeout(300)
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

                    fuel_raw = get_attr_any(items, ["kraftstoff", "treibstoff"])
                    trans_raw = get_attr_any(items, ["getriebe"])
                    drive_raw = get_attr_any(items, ["antrieb", "allrad"])
                    body_raw = get_attr_any(items, ["karosserie", "bauart"])

                    desc_el = page.query_selector('[data-testid="description"]')
                    description = desc_el.inner_text().strip() if desc_el else None

                    features_raw = []
                    blob = " ".join([t for t in [title, description] if t]).lower()

                    feature_rules = {
                        "carplay": ["carplay"],
                        "android_auto": ["android auto"],
                        "acc": ["acc", "adaptiver tempomat"],
                        "led": ["led", "matrix", "xenon"],
                        "sitzheizung": ["sitzheizung"],
                        "allrad": ["quattro", "xdrive", "4motion", "allrad"],
                        "navi": ["navi", "navigation"],
                    }

                    for k, needles in feature_rules.items():
                        if any(n in blob for n in needles):
                            features_raw.append(k)

                    brand, model = None, None
                    if title:
                        parts = title.split()
                        if len(parts) > 0:
                            brand = parts[0]
                        if len(parts) > 1:
                            model = parts[1]

                    car = {
                        "platform": "willhaben",
                        "external_id": extract_external_id(url),
                        "url": url,
                        "title": title,
                        "brand": brand,
                        "model": model,
                        "year": year,
                        "km": km,
                        "price": price,
                        "power_ps": power_ps,
                        "fuel_type": fuel_raw,
                        "transmission": trans_raw,
                        "drive": drive_raw,
                        "body_type": body_raw,
                        "variant": None,
                        "seller_type": None,
                        "location": None,
                        "features_raw": features_raw,
                        "description": description,
                    }

                    insert_car(car)
                    log(f"[W{worker_id}] Gespeichert")

                except Exception as e:
                    log(f"[W{worker_id}] Fehler: {e}")

                finally:
                    queue.task_done()

            page.close()


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

        def block_resources(route):
            req = route.request
            rtype = req.resource_type
            url = req.url

            if rtype in ("image", "media", "font"):
                return route.abort()

            # optional: analytics/tracking blocken
            if any(x in url for x in ["google-analytics", "doubleclick", "facebook", "clarity", "hotjar"]):
                return route.abort()

            return route.continue_()

        context.route("**/*", block_resources)

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

            if car_exists(url):
                log(f"Skip (bereits bekannt): {url}")
                continue

            log(f"Inserat {idx}/{len(ad_links)}: {url}")
            try:
                page.goto(url, wait_until="commit", timeout=30000)
                page.wait_for_timeout(300)
                accept_cookies(page)

                title_el = page.query_selector("h1")
                title = title_el.inner_text().strip() if title_el else None

                price_el = page.query_selector('span[data-testid^="contact-box-price-box-price-value"]')
                price = parse_int(price_el.inner_text()) if price_el else None

                items = page.query_selector_all('li[data-testid="attribute-item"]')
                km_raw = get_attribute(items, "kilometer")
                year_raw = get_attribute(items, "erstzulassung")
                power_raw = get_attribute(items, "leistung")
                fuel_raw = get_attr_any(items, ["kraftstoff", "treibstoff"])
                trans_raw = get_attr_any(items, ["getriebe"])
                drive_raw = get_attr_any(items, ["antrieb", "allrad"])
                body_raw = get_attr_any(items, ["karosserie", "bauart"])
                variant_raw = get_attr_any(items, ["ausstattungslinie", "modellvariante", "version"])
                desc_el = page.query_selector('[data-testid="description"]')
                description = desc_el.inner_text().strip() if desc_el else None

                features_raw = []
                text_blob = " ".join([t for t in [title, description] if t])
                blob = text_blob.lower()

                feature_rules = {
                    "carplay": ["carplay", "apple carplay"],
                    "android_auto": ["android auto"],
                    "acc": ["acc", "adaptiver tempomat", "abstandsregeltempomat"],
                    "led": [" led", "matrix", "xenon"],
                    "sitzheizung": ["sitzheizung"],
                    "allrad": ["quattro", "xdrive", "4motion", "allrad"],
                    "navi": ["navi", "navigation", "mmi", "comand"],
                    "sportpaket": ["s line", "s-line", "m paket", "m-paket", "r-line"],
                    "anhängerkupplung": ["anhängerkupplung", "ahk"],
                    "parkassist": ["parkassistent", "einparkhilfe", "pdc", "parkpilot"],
                }

                for key, needles in feature_rules.items():
                    if any(n in blob for n in needles):
                        features_raw.append(key)

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
                    "fuel_type": fuel_raw,
                    "transmission": trans_raw,
                    "drive": drive_raw,
                    "body_type": body_raw,
                    "variant": variant_raw,
                    "features_raw": features_raw,
                    "description": description,
                    "seller_type": None,


                }

                log(f"EXTRA: fuel={fuel_raw}, trans={trans_raw}, drive={drive_raw}, feats={features_raw}")
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

    url = build_search_url(sfId=WILLHABEN_SFID, rows=60, page=1)
    run_scrape(url, headless=False)
