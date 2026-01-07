from config import WILLHABEN_SFID
from willhaben_url import build_search_url
from scrapers.scrape_willhaben_async import run_scrape
from tools.extract_from_url import extract_profile
from datetime import datetime

def make_file_logger(name: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    path = f"logs/{ts}_{safe}.log"
    import os
    os.makedirs("logs", exist_ok=True)

    def logger(msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return logger, path


URLS = [
"https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?sfId=073c28e0-506f-4d1b-a9da-362014b549d5&isNavigation=true&CAR_MODEL/MAKE=1065&CAR_MODEL/MODEL=1691&YEAR_MODEL_FROM=2018&MILEAGE_TO=100000&PRICE_TO=15000",
"https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?sfId=073c28e0-506f-4d1b-a9da-362014b549d5&isNavigation=true&CAR_MODEL/MAKE=1056&CAR_MODEL/MODEL=1590&YEAR_MODEL_FROM=2016&MILEAGE_TO=100000&PRICE_TO=15000",
"https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse?sfId=073c28e0-506f-4d1b-a9da-362014b549d5&isNavigation=true&CAR_MODEL/MAKE=1057&CAR_MODEL/MODEL=1600&YEAR_MODEL_FROM=2018&MILEAGE_TO=100000&PRICE_TO=20000",
]

def main():
    for i, u in enumerate(URLS, start=1):
        p = extract_profile(u)

        # sfId: wenn in URL keiner drin ist, nimm den aus config
        sfid = p["sfId"] or WILLHABEN_SFID

        start_url = build_search_url(
            sfId=sfid,
            make_id=p["make_id"],
            model_ids=p["model_ids"] or None,
            year_from=p["year_from"],
            year_to=p["year_to"],
            mileage_from=p["mileage_from"],
            mileage_to=p["mileage_to"],
            price_from=p["price_from"],
            price_to=p["price_to"],
            rows=p["rows"] or 30,
            page=1,
        )

        logger, path = make_file_logger(f"search_{i}")
        print("Logfile:", path)
        run_scrape(start_url, log_cb=logger, headless=True)

        print(f"\n=== Suche {i}/{len(URLS)} ===")
        print(start_url)
        run_scrape(start_url, log_cb=print, headless=True)

if __name__ == "__main__":
    main()
