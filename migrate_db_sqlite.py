import sqlite3

DB_PATH = "auto_deal.db"

def col_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

def add_col(cur, table, col, coltype):
    if not col_exists(cur, table, col):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
        print(f"Added {table}.{col}")
    else:
        print(f"Exists {table}.{col}")

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Zeitspalten
    add_col(cur, "cars", "first_seen", "TEXT")
    add_col(cur, "cars", "last_seen", "TEXT")

    # Deine neuen Analyse-Spalten (falls noch nicht da)
    for col, typ in [
        ("power_ps", "INTEGER"),
        ("fuel_type", "TEXT"),
        ("transmission", "TEXT"),
        ("drive", "TEXT"),
        ("body_type", "TEXT"),
        ("variant", "TEXT"),
        ("seller_type", "TEXT"),
        ("features_raw", "TEXT"),
        ("description", "TEXT"),
    ]:
        add_col(cur, "cars", col, typ)

    # price_history (optional, aber sinnvoll)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER NOT NULL,
        price INTEGER,
        seen_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (car_id) REFERENCES cars(id)
    )
    """)

    con.commit()
    con.close()
    print("Migration fertig.")

if __name__ == "__main__":
    main()
