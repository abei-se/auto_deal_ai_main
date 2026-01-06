print("test_run gestartet")

from scrapers.scrape_willhaben import run_scrape
print("run_scrape import OK:", run_scrape)

from config import WILLHABEN_SFID
from willhaben_url import build_search_url

start_url = build_search_url(
    sfId=WILLHABEN_SFID,
    make_id=1003,
    model_ids=[1024],
    year_from=2018,
    mileage_to=150000,
    price_to=30000,
    page=1,
)

print("start_url:", start_url)

def logger(msg):
    print("[SCRAPER]", msg)

run_scrape(start_url, log_cb=logger)

print("test_run fertig")
