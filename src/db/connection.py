import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def get_engine():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    
    if password:
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    else:
        url = f"postgresql+psycopg2://{user}@{host}:{port}/{dbname}"

    return create_engine(url)