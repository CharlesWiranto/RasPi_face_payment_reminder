from database import init_db
from config import Config

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print(f"Database initialized at {Config.DATABASE_URI}")