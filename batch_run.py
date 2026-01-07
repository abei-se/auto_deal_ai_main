from datetime import datetime
from config import WILLHABEN_SFID
from willhaben_url import build_search_url
from scrapers.scrape_willhaben import run_scrape

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

SEARCHES = [
    {
        "name": "Audi A3 ab 2018 bis 150k km bis 30k",
        "make_id": 1003,
        "model_ids": [1024],      # A3 (deine ID)
        "year_from": 2018,
        "mileage_to": 150000,
        "price_to": 30000,
    },
    {
        "name": "Audi A4 ab 2017 bis 180k km bis 28k",
        "make_id": 1003,
        "model_ids": [2065],      # A4 (deine ID aus Beispiel)
        "year_from": 2017,
        "mileage_to": 180000,
        "price_to": 28000,
    },
    {
        "name": "BMW 3er ab 2016 bis 180k km bis 25k",
        "make_id": 1025,          # Beispiel-ID, bitte anpassen
        "model_ids": [],          # leer = alle Modelle der Marke
        "year_from": 2016,
        "mileage_to": 180000,
        "price_to": 25000,
    },
]

def main():
    for i, s in enumerate(SEARCHES, start=1):
        log(f"=== Suche {i}/{len(SEARCHES)}: {s['name']} ===")

        url = build_search_url(
            sfId=WILLHABEN_SFID,
            make_id=s.get("make_id"),
            model_ids=s.get("model_ids") or None,
            year_from=s.get("year_from"),
            year_to=s.get("year_to"),
            mileage_from=s.get("mileage_from"),
            mileage_to=s.get("mileage_to"),
            price_from=s.get("price_from"),
            price_to=s.get("price_to"),
            rows=30,
            page=1,
        )

        log(f"URL: {url}")
        run_scrape(url, log_cb=log, headless=True)

    log("Alle Suchen fertig.")

if __name__ == "__main__":
    main()
