from playwright.sync_api import sync_playwright
import json
import time

SEARCH_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"


def accept_cookies(page):
    try:
        page.locator('button:has-text("Alle akzeptieren")').first.click(timeout=5000)
        time.sleep(1)
    except:
        pass


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        accept_cookies(page)
        time.sleep(3)

        # 🔑 ZENTRALER PUNKT: Next.js State auslesen
        data = page.evaluate("""
            () => {
                return window.__NEXT_DATA__;
            }
        """)

        browser.close()

    # 🔍 Datenstruktur extrahieren
    try:
        search_result = data["props"]["pageProps"]["searchResult"]
        nav_groups = search_result.get("navigationGroups", [])

    except KeyError:
        raise Exception("❌ Konnte Filter-Daten nicht finden – Willhaben-Struktur geändert")

    brands = {}
    models = {}

    for group in nav_groups:
        if group.get("id") == "CAR_MODEL/MAKE":
            for item in group.get("items", []):
                brands[item["label"]] = item["value"]
                models[item["label"]] = []

        if group.get("id") == "CAR_MODEL/MODEL":
            for item in group.get("items", []):
                parent = item.get("parentLabel")
                if parent in models:
                    models[parent].append({
                        "name": item["label"],
                        "id": item["value"]
                    })


    # 💾 Speichern
    with open("brands.json", "w", encoding="utf-8") as f:
        json.dump(brands, f, indent=2, ensure_ascii=False)

    with open("models.json", "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(brands)} Marken gespeichert")
    print("✅ models.json gespeichert")


if __name__ == "__main__":
    run()
