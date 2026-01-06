# export_excel.py
import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URL

def export_to_excel(out_path: str, where_sql: str = "", params: dict | None = None):
    engine = create_engine(DATABASE_URL, future=True)
    query = "SELECT * FROM cars"
    if where_sql.strip():
        query += f" WHERE {where_sql}"
    query += " ORDER BY last_seen DESC"

    df = pd.read_sql_query(query, engine, params=params or {})
    df.to_excel(out_path, index=False)

    return len(df)

if __name__ == "__main__":
    n = export_to_excel("export.xlsx")
    print(f"Exported {n} rows")
