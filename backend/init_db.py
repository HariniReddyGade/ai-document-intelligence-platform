from app.database import Base, engine
from app.models import Document, DocumentQuestion


def initialize_database():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    initialize_database()