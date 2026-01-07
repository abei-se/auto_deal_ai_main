import json
import re
from playwright.sync_api import sync_playwright

START_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?isNavigation=true&CAR_TYPE=6&rows=30&page=1"
ID_RE = re.compile(r'"id"\s*:\s*(\d+).{0,40}?"(name|label|displayName)"\s*:\s*"([^"]+)"', re.I | re.S)

def main():
    hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                if "application/json" not in ct:
                    return
                txt = resp.text()
                if len(txt) > 2_000_000:
                    return
                for m in ID_RE.finditer(txt):
                    _id = int(m.group(1))
                    _name = m.group(3)
                    if 1 <= len(_name) <= 60:
                        hits.append((_id, _name, resp.url))
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        browser.close()

    # dedupe
    uniq = {}
    for _id, _name, _url in hits:
        uniq[(_id, _name)] = _url

    out = [{"id": k[0], "name": k[1], "source_url": uniq[k]} for k in uniq]
    out = sorted(out, key=lambda x: (x["name"].lower(), x["id"]))

    with open("api_id_candidates.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Geschrieben: api_id_candidates.json ({len(out)} Kandidaten)")
    print("Suche in der Datei nach 'Audi' oder 'A3'.")

if __name__ == "__main__":
    main()
