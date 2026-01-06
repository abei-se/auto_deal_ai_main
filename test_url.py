from config import WILLHABEN_SFID
from willhaben_url import build_search_url

url = build_search_url(
    sfId=WILLHABEN_SFID,
    make_id=1003,          # Audi
    model_ids=[1025, 2065],# mehrere Modelle
    year_from=2005,
    mileage_to=150000,
    price_to=30000,
    rows=30,
    page=1,
)

print(url)
