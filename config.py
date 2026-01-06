#DB_URL = "postgresql+psycopg2:///abdulahsecibovic@localhost:5432/auto_deals"

#EMAIL_HOST = "smtp.gmail.com"
#EMAIL_PORT = 465
#EMAIL_USER = "secibovic.abdulah@gmail.com"
#EMAIL_PASS = "jooh sshq nwqu leob"
#EMAIL_TO = "selmirs@hotmail.com"

# PostgreSQL Konfiguration

DB_USER = "autodeals"
DB_PASSWORD = ""      # leer lassen, wenn du kein Passwort gesetzt hast
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "auto_deals"

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
