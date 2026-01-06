# init_db.py
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def init_db():
    engine = create_engine(DATABASE_URL, future=True)
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            external_id TEXT,
            title TEXT,
            brand TEXT,
            model TEXT,
            year INTEGER,
            km INTEGER,
            price INTEGER,
            location TEXT,
            url TEXT UNIQUE,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))
    return engine

if __name__ == "__main__":
    init_db()
    print("DB ready")
