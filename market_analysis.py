import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "auto_deal.db")
OUT_DIR = "exports"

def load_cars(db_path: str) -> pd.DataFrame:
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM cars", con)
    con.close()
    return df

def to_num(series):
    return pd.to_numeric(series, errors="coerce")

def main():
    df = load_cars(DB_PATH)

    if df.empty:
        print("Keine Daten in cars.")
        return

    # Grundreinigung
    for col in ["price", "km", "year", "power_ps"]:
        if col in df.columns:
            df[col] = to_num(df[col])

    # Nur brauchbare Zeilen für Preis-Analyse
    need_cols = ["price", "year", "km", "brand", "model"]
    for c in need_cols:
        if c not in df.columns:
            raise RuntimeError(f"Spalte fehlt in cars: {c}")

    df = df.dropna(subset=["price", "year", "km", "brand", "model"]).copy()

    # Optional: nur realistische Werte
    df = df[(df["price"] > 500) & (df["price"] < 200000)]
    df = df[(df["km"] >= 0) & (df["km"] < 600000)]
    df = df[(df["year"] >= 1990) & (df["year"] <= datetime.now().year + 1)]

    # Optional: nur neuere Einträge (wenn last_seen existiert)
    if "last_seen" in df.columns:
        df["last_seen_dt"] = pd.to_datetime(df["last_seen"], errors="coerce")
        # zB letzte 30 Tage, kannst du ändern
        cutoff = datetime.now() - timedelta(days=30)
        df = df[df["last_seen_dt"].isna() | (df["last_seen_dt"] >= cutoff)].copy()

    # Analyse-Gruppierung: so findest du faire Vergleichsgruppen
    # Transmission, fuel_type, drive, power_ps sind optional, wenn vorhanden.
    group_cols = ["brand", "model"]

    if "year" in df.columns:
        # Jahr als "Jahr-Bucket", damit Gruppen stabiler sind
        df["year_bucket"] = (df["year"] // 2) * 2  # 2-Jahres-Buckets: 2018, 2020, ...
        group_cols.append("year_bucket")

    if "power_ps" in df.columns:
        # PS-Buckets: 10er Schritte
        df["ps_bucket"] = (df["power_ps"] // 10) * 10
        group_cols.append("ps_bucket")

    for optional in ["transmission", "fuel_type", "drive"]:
        if optional in df.columns:
            group_cols.append(optional)

    # Marktstatistiken pro Gruppe
    agg = df.groupby(group_cols).agg(
        n=("price", "count"),
        median_price=("price", "median"),
        q25=("price", lambda s: s.quantile(0.25)),
        q75=("price", lambda s: s.quantile(0.75)),
        median_km=("km", "median"),
    ).reset_index()

    # Nur Gruppen mit genug Daten, sonst wird Median wackelig
    agg = agg[agg["n"] >= 8].copy()

    # Daten zurück mergen
    merged = df.merge(agg, on=group_cols, how="inner")

    # Deal Score
    merged["price_delta"] = merged["price"] - merged["median_price"]
    merged["deal_ratio"] = merged["price"] / merged["median_price"]

    # optional: IQR-based "sehr günstig"
    merged["iqr"] = merged["q75"] - merged["q25"]
    merged["is_outlier_low"] = merged["price"] < (merged["q25"] - 0.5 * merged["iqr"])

    # Ranking: zuerst stärkste Unterbewertung
    deals = merged.sort_values(["deal_ratio", "price_delta"]).copy()

    # Gute Deals definieren: zB 15% unter Median oder starker IQR-Ausreißer
    deals = deals[(deals["deal_ratio"] <= 0.85) | (deals["is_outlier_low"] == True)].copy()

    # Spalten fürs Reporting
    cols = [
        "brand", "model",
        "year", "km", "power_ps",
        "fuel_type", "transmission", "drive",
        "price",
        "median_price", "price_delta", "deal_ratio",
        "n", "median_km",
        "url", "title",
    ]
    cols = [c for c in cols if c in deals.columns]

    deals_report = deals[cols].copy()
    summary_report = agg.sort_values(["n", "median_price"], ascending=[False, True]).copy()

    # Ausgabe
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUT_DIR, f"market_deals_{ts}.xlsx")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        deals_report.head(200).to_excel(writer, index=False, sheet_name="TopDeals")
        summary_report.to_excel(writer, index=False, sheet_name="MarketSummary")

    print(f"Fertig. Export: {out_path}")
    print(f"Deals gefunden: {len(deals_report)}")
    print(f"Gruppen im Summary: {len(summary_report)}")

if __name__ == "__main__":
    main()
