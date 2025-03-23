from sqlalchemy import create_engine, MetaData

DATABASE_URL = "mysql+mysqlconnector://root:ammar@localhost:3306/database_1"

engine = create_engine(DATABASE_URL, echo=True)  # <- This shows SQL commands

metadata = MetaData()
metadata.create_all(engine)
print("Tables created successfully.")
