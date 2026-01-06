from sqlalchemy import create_engine, text
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)

def insert_car(car):
    query = text("""
    INSERT INTO cars (
      platform, external_id, title, brand, model, year, km, price, location, url, last_seen
    ) VALUES (
      :platform, :external_id, :title, :brand, :model, :year, :km, :price, :location, :url, CURRENT_TIMESTAMP
    )
    ON CONFLICT(url) DO UPDATE SET
      price = excluded.price,
      km = excluded.km,
      last_seen = CURRENT_TIMESTAMP;
    """)
    with engine.begin() as conn:
        conn.execute(query, car)
