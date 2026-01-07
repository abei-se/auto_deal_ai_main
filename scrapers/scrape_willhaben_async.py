import os
import sys
import re
import json
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from db import insert_car

REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "4"))


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

def get_attribute_from_kv(kv_list, keyword):
    keyword = keyword.lower()
    for title, value in kv_list:
        if keyword in (title or "").strip().lower():
            return (value or "").strip()
    return None

def extract_external_id(url):
    m = re.search(r"-([0-9]{6,})/?$", url)
    if m:
        return m.group(1)
    m2 = re.search(r"/([0-9]{6,})/?$", url)
    return m2.group(1) if m2 else url

async def accept_cookies(page):
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
            if await loc.is_visible(timeout=800):
                await loc.click(timeout=1500)
                await page.wait_for_timeout(250)
                return True
        except Exception:
            continue
    return False

async def scroll_until_all_loaded(page, log, max_rounds=20):
    last_count = 0
    stable = 0
    for i in range(max_rounds):
        await page.mouse.wheel(0, 900)
        await page.wait_for_timeout(700)

        links = await page.query_selector_all('a[href^="/iad/gebrauchtwagen/d/auto/"]')
        hrefs = set()
        for el in links:
            h = await el.get_attribute("href")
            if h:
                hrefs.add(h)

        current = len(hrefs)
        log(f"Scroll {i+1}: {current} Inserate")

        if current == last_count:
            stable += 1
        else:
            stable = 0
        if stable >= 2:
            break
        last_count = current

async def block_resources(route):
    req = route.request
    rtype = req.resource_type
    url = req.url

    if rtype in ("image", "media", "font"):
        await route.abort()
        return

    if any(x in url for x in ["google-analytics", "doubleclick", "facebook", "clarity", "hotjar", "adsystem"]):
        await route.abort()
        return

    await route.continue_()

def extract_features(title, description):
    features = []
    blob = " ".join([t for t in [title, description] if t]).lower()

    rules = {
        "carplay": ["carplay"],
        "android_auto": ["android auto"],
        "acc": ["acc", "adaptiver tempomat", "abstandsregeltempomat"],
        "led": [" led", "matrix", "xenon"],
        "sitzheizung": ["sitzheizung"],
        "allrad": ["quattro", "xdrive", "4motion", "allrad"],
        "navi": ["navi", "navigation", "mmi", "comand"],
        "sportpaket": ["s line", "s-line", "m paket", "m-paket", "r-line"],
        "anhängerkupplung": ["anhängerkupplung", "ahk"],
    }
    for k, needles in rules.items():
        if any(n in blob for n in needles):
            features.append(k)
    return features

async def parse_detail(context, url, log):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="commit", timeout=30000)
        await page.wait_for_timeout(250)
        await accept_cookies(page)

        title_el = await page.query_selector("h1")
        title = (await title_el.inner_text()).strip() if title_el else None

        price_el = await page.query_selector('span[data-testid^="contact-box-price-box-price-value"]')
        price = parse_int((await price_el.inner_text()).strip()) if price_el else None

        # attribute items -> build kv list once (faster than querying each time)
        kv = []
        items = await page.query_selector_all('li[data-testid="attribute-item"]')
        for it in items:
            t = await it.query_selector('[data-testid="attribute-title"]')
            v = await it.query_selector('[data-testid="attribute-value"]')
            if t and v:
                kv.append(((await t.inner_text()).strip(), (await v.inner_text()).strip()))

        km_raw = get_attribute_from_kv(kv, "kilometer")
        year_raw = get_attribute_from_kv(kv, "erstzulassung")
        power_raw = get_attribute_from_kv(kv, "leistung")
        fuel_raw = get_attribute_from_kv(kv, "kraftstoff") or get_attribute_from_kv(kv, "treibstoff")
        trans_raw = get_attribute_from_kv(kv, "getriebe")
        drive_raw = get_attribute_from_kv(kv, "antrieb") or get_attribute_from_kv(kv, "allrad")
        body_raw = get_attribute_from_kv(kv, "karosserie") or get_attribute_from_kv(kv, "bauart")

        km = parse_int(km_raw)
        year = int(year_raw.split("/")[-1]) if year_raw and "/" in year_raw else None
        power_ps = parse_power_ps(power_raw)

        desc_el = await page.query_selector('[data-testid="description"]')
        description = (await desc_el.inner_text()).strip() if desc_el else None

        brand, model = None, None
        if title:
            parts = title.split()
            if len(parts) > 0:
                brand = parts[0]
            if len(parts) > 1:
                model = parts[1]

        feats = extract_features(title, description)

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
            "features_raw": json.dumps(feats, ensure_ascii=False),
            "description": description,
        }

        insert_car(car)
        log(f"Gespeichert: {url}")

    finally:
        await page.close()

async def worker(name, context, queue, log):
    while True:
        url = await queue.get()
        if url is None:
            queue.task_done()
            return
        try:
            log(f"[{name}] {url}")
            await parse_detail(context, url, log)
        except PlaywrightTimeoutError as e:
            log(f"[{name}] Timeout: {e}")
        except Exception as e:
            log(f"[{name}] Fehler: {e}")
        finally:
            queue.task_done()

def run_scrape(start_url: str, log_cb=print, headless: bool = True):
    def log(msg: str):
        try:
            log_cb(str(msg))
        except Exception:
            print(str(msg))

    async def runner():
        log(f"run_scrape gestartet: {start_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent=REAL_UA,
                locale="de-AT",
                timezone_id="Europe/Vienna",
                viewport={"width": 1280, "height": 800}
            )

            await context.route("**/*", block_resources)

            page = await context.new_page()

            await page.goto("https://www.willhaben.at", wait_until="domcontentloaded")
            await page.wait_for_timeout(900)
            clicked = await accept_cookies(page)
            log(f"Cookie Accept (home): {'ok' if clicked else 'nicht gefunden/ignoriert'}")

            await page.goto(start_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(900)
            clicked = await accept_cookies(page)
            log(f"Cookie Accept (search): {'ok' if clicked else 'nicht gefunden/ignoriert'}")

            all_links = set()
            page_number = 1

            while True:
                log(f"Seite {page_number}")
                await scroll_until_all_loaded(page, log, max_rounds=12)

                link_elements = await page.query_selector_all('a[href^="/iad/gebrauchtwagen/d/auto/"]')
                for el in link_elements:
                    href = await el.get_attribute("href")
                    if href:
                        all_links.add("https://www.willhaben.at" + href)

                log(f"Gesammelte Inserate gesamt: {len(all_links)}")

                next_page = page_number + 1
                next_btn = await page.query_selector(f'a[aria-label="Zur Seite {next_page}"]')
                if not next_btn:
                    log("Keine weitere Seite gefunden")
                    break

                log(f"Wechsle zu Seite {next_page}")
                await next_btn.click()
                await page.wait_for_timeout(1800)
                page_number += 1

            ad_links = list(all_links)
            log(f"Starte Parallel-Detailverarbeitung mit {MAX_WORKERS} Workern")

            q = asyncio.Queue()
            for u in ad_links:
                await q.put(u)
            for _ in range(MAX_WORKERS):
                await q.put(None)

            tasks = []
            for i in range(MAX_WORKERS):
                tasks.append(asyncio.create_task(worker(f"W{i+1}", context, q, log)))

            await q.join()
            await asyncio.gather(*tasks)

            await page.close()
            await context.close()
            await browser.close()

            log("Alle Inserate gespeichert")

    asyncio.run(runner())
