import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="auto_deals",
    user="autodeals",
    password="armin-selmir187!"
)

cursor = conn.cursor()

cursor.execute("SELECT version();")
version = cursor.fetchone()

print("PostgreSQL Version:", version)

cursor.close()
conn.close()
