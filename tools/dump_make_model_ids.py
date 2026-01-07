import json
from playwright.sync_api import sync_playwright

START_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?isNavigation=true&CAR_TYPE=6&rows=30&page=1"

def walk(obj, results, path=""):
    # Suche nach Strukturen, die wie (id,label) aussehen
    if isinstance(obj, dict):
        # Kandidat: dict enthält "id" und einen Namen
        if "id" in obj and any(k in obj for k in ["label", "name", "text", "displayName"]):
            name_key = next((k for k in ["label", "name", "text", "displayName"] if k in obj), None)
            if name_key:
                _id = obj.get("id")
                _name = obj.get(name_key)
                if isinstance(_id, int) and isinstance(_name, str) and 1 <= len(_name) <= 60:
                    results.append((_id, _name, path))

        for k, v in obj.items():
            walk(v, results, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, results, path + f"[{i}]")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        data = page.evaluate("() => window.__NEXT_DATA__ || null")
        browser.close()

    if not data:
        raise RuntimeError("Konnte window.__NEXT_DATA__ nicht lesen.")

    results = []
    walk(data, results)

    # Heuristik: wir suchen die häufigsten Namen, um „Brands“ und „Models“ zu finden
    # Du bekommst trotzdem alle Kandidaten, wir filtern nur grob für Übersicht
    unique = {}
    for _id, _name, _path in results:
        key = (_id, _name)
        if key not in unique:
            unique[key] = _path

    # Ausgabe als JSON, damit du es später direkt nutzen kannst
    out = [{"id": k[0], "name": k[1], "path": unique[k]} for k in unique]
    out_sorted = sorted(out, key=lambda x: (x["name"].lower(), x["id"]))

    with open("next_data_id_candidates.json", "w", encoding="utf-8") as f:
        json.dump(out_sorted, f, ensure_ascii=False, indent=2)

    print(f"Geschrieben: next_data_id_candidates.json ({len(out_sorted)} Kandidaten)")
    print("Tipp: Öffne die Datei und suche nach 'Audi', 'BMW', 'Golf', 'A3'.")

if __name__ == "__main__":
    main()
