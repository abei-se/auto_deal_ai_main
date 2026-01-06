from sqlalchemy import create_engine, text
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)


def insert_search_filter(name, base_url):
    query = """
    INSERT INTO search_filters (name, base_url)
    VALUES (:name, :base_url)
    """
    with engine.begin() as conn:
        conn.execute(text(query), {
            "name": name,
            "base_url": base_url
        })


def insert_car(car):
    query = text("""
        INSERT INTO cars (
            platform,
            external_id,
            title,
            brand,
            model,
            year,
            km,
            price,
            location,
            url
        )
        VALUES (
            :platform,
            :external_id,
            :title,
            :brand,
            :model,
            :year,
            :km,
            :price,
            :location,
            :url
        )
        ON CONFLICT (url) DO UPDATE
        SET
            price = EXCLUDED.price,
            km = EXCLUDED.km,
            last_seen = NOW();
    """)

    with engine.begin() as conn:
        conn.execute(query, car)
