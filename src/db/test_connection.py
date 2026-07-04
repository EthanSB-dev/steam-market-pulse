from connection import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
    ))
    tables = [row[0] for row in result]
    print("Connected! Tables found:", tables)