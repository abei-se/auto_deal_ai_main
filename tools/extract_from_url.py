from urllib.parse import urlparse, parse_qs

def extract_profile(url: str) -> dict:
    qs = parse_qs(urlparse(url).query)

    def one_int(key: str):
        v = qs.get(key)
        return int(v[0]) if v and v[0].isdigit() else None

    def many_int(key: str):
        v = qs.get(key, [])
        out = []
        for x in v:
            try:
                out.append(int(x))
            except Exception:
                pass
        return out

    profile = {
        "sfId": (qs.get("sfId") or [None])[0],
        "make_id": one_int("CAR_MODEL/MAKE"),
        "model_ids": many_int("CAR_MODEL/MODEL"),
        "year_from": one_int("YEAR_MODEL_FROM"),
        "year_to": one_int("YEAR_MODEL_TO"),
        "mileage_from": one_int("MILEAGE_FROM"),
        "mileage_to": one_int("MILEAGE_TO"),
        "price_from": one_int("PRICE_FROM"),
        "price_to": one_int("PRICE_TO"),
        "rows": one_int("rows") or 30,
        "page": one_int("page") or 1,
    }
    return profile

if __name__ == "__main__":
    url = input("Willhaben URL: ").strip()
    print(extract_profile(url))
