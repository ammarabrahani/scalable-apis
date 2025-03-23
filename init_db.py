from sqlalchemy import create_engine
from models import metadata

DATABASE_URL = "mysql+mysqlconnector://fastapi:yourpassword@localhost:3306/database_1"

engine = create_engine(DATABASE_URL, echo=True)  # <- This shows SQL commands

metadata = MetaData()
metadata.create_all(engine)
print("Tables created successfully.")
