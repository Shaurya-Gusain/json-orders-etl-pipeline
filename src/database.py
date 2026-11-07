import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "orders_db")
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT DATABASE()")
            )

            print("Connected to database:", result.scalar())

    except Exception as e:
        print("Database connection failed:", e)


if __name__ == "__main__":
    test_connection()