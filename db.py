import json
from sqlalchemy import create_engine, text
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)

def insert_car(car: dict):
    # features_raw als JSON-Text
    if isinstance(car.get("features_raw"), (list, dict)):
        car["features_raw"] = json.dumps(car["features_raw"], ensure_ascii=False)

    with engine.begin() as conn:
        # 1) Upsert cars (SQLite)
        car.setdefault("seller_type", None)
        car.setdefault("location", None)
        car.setdefault("variant", None)
        car.setdefault("body_type", None)
        car.setdefault("features_raw", "[]")
        car.setdefault("description", None)
        car.setdefault("fuel_type", None)
        car.setdefault("transmission", None)
        car.setdefault("drive", None)
        car.setdefault("power_ps", None)

        conn.execute(text("""
            INSERT INTO cars (
                platform, external_id, url, title,
                brand, model, variant, body_type,
                year, km, price, power_ps,
                fuel_type, transmission, drive,
                seller_type, location, features_raw, description,
                first_seen, last_seen
            )
            VALUES (
                :platform, :external_id, :url, :title,
                :brand, :model, :variant, :body_type,
                :year, :km, :price, :power_ps,
                :fuel_type, :transmission, :drive,
                :seller_type, :location, :features_raw, :description,
                datetime('now'), datetime('now')
            )
            ON CONFLICT(url) DO UPDATE SET
                external_id=excluded.external_id,
                title=excluded.title,
                brand=excluded.brand,
                model=excluded.model,
                variant=excluded.variant,
                body_type=excluded.body_type,
                year=excluded.year,
                km=excluded.km,
                price=excluded.price,
                power_ps=excluded.power_ps,
                fuel_type=excluded.fuel_type,
                transmission=excluded.transmission,
                drive=excluded.drive,
                seller_type=excluded.seller_type,
                location=excluded.location,
                features_raw=excluded.features_raw,
                description=excluded.description,
                last_seen=datetime('now')
        """), car)

        # 2) car_id holen
        car_id = conn.execute(text("SELECT id FROM cars WHERE url=:url"), {"url": car["url"]}).scalar_one()

        # 3) letzten Preis holen, nur bei Änderung schreiben
        last_price = conn.execute(text("""
            SELECT price FROM price_history WHERE car_id=:car_id
            ORDER BY seen_at DESC LIMIT 1
        """), {"car_id": car_id}).scalar()

        if car.get("price") is not None and (last_price is None or int(last_price) != int(car["price"])):
            conn.execute(text("""
                INSERT INTO price_history (car_id, price) VALUES (:car_id, :price)
            """), {"car_id": car_id, "price": car["price"]})

from sqlalchemy import text

def car_exists(url: str) -> bool:
    with engine.begin() as conn:
        res = conn.execute(
            text("SELECT 1 FROM cars WHERE url = :url LIMIT 1"),
            {"url": url}
        ).first()
        return res is not None
