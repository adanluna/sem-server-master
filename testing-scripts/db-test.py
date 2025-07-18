from psycopg import connect
import os
from dotenv import load_dotenv

load_dotenv()

dsn = f"host={os.getenv('DB_HOST')} port={os.getenv('DB_PORT')} dbname={os.getenv('DB_NAME')} user={os.getenv('DB_USER')} password={os.getenv('DB_PASS')}"

conn = connect(dsn)
print("✅ Conexión exitosa a PostgreSQL desde tu Mac")
conn.close()
