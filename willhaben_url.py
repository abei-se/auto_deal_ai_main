from urllib.parse import urlencode, urlparse, parse_qs

BASE = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"

def extract_sfid(url: str) -> str | None:
    qs = parse_qs(urlparse(url).query)
    v = qs.get("sfId")
    return v[0] if v else None

def build_search_url(
    *,
    sfId: str,
    make_id: int | None = None,
    model_ids: list[int] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    mileage_from: int | None = None,
    mileage_to: int | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    rows: int = 30,
    page: int = 1,
    car_type: int = 6,
) -> str:
    params: list[tuple[str, str]] = [
        ("sfId", sfId),
        ("isNavigation", "true"),
        ("CAR_TYPE", str(car_type)),
        ("rows", str(rows)),
        ("page", str(page)),
    ]

    if make_id is not None:
        params.append(("CAR_MODEL/MAKE", str(make_id)))

    if model_ids:
        for mid in model_ids:
            params.append(("CAR_MODEL/MODEL", str(mid)))

    if year_from is not None:
        params.append(("YEAR_MODEL_FROM", str(year_from)))
    if year_to is not None:
        params.append(("YEAR_MODEL_TO", str(year_to)))

    if mileage_from is not None:
        params.append(("MILEAGE_FROM", str(mileage_from)))
    if mileage_to is not None:
        params.append(("MILEAGE_TO", str(mileage_to)))

    if price_from is not None:
        params.append(("PRICE_FROM", str(price_from)))
    if price_to is not None:
        params.append(("PRICE_TO", str(price_to)))

    return f"{BASE}?{urlencode(params)}"
