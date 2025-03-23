import os
import logging
from sqlalchemy import create_engine, MetaData
from databases import Database
from dotenv import load_dotenv

# ✅ Load Environment Variables
load_dotenv()

# ✅ Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ✅ Connection URL for SQLAlchemy
DATABASE_URL = "mysql+mysqlconnector://fastapi:yourpassword@localhost:3306/database_1"

logger.info(f"Database URL: {DATABASE_URL}")

# ✅ Async Database Connection
database = Database(DATABASE_URL)

# ✅ SQLAlchemy Metadata
metadata = MetaData()

# ✅ SQLAlchemy Engine
engine = create_engine(DATABASE_URL, echo=True)

# ✅ Ensure Tables Are Created
def create_tables():
    metadata.create_all(engine)
    print("✅ Tables created successfully.")

# ✅ Run Table Creation
if __name__ == "__main__":
    create_tables()
