import sys
import os

# Add the project root to sys.path so we can import 'backend'
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend import models

def clear_database():
    db = SessionLocal()
    try:
        print("LOG: Clearing all database records...")
        
        # Delete in proper order to respect Foreign Key constraints
        # 1. Quiz Results (referencing Tasks and Goals)
        db.query(models.QuizResult).delete()
        # 2. Tasks (referencing Goals)
        db.query(models.Task).delete()
        # 3. Goals (referencing Users)
        db.query(models.Goal).delete()
        # 4. Users
        db.query(models.User).delete()
        
        db.commit()
        print("✅ SUCCESS: Database content cleared. Schema is intact.")
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: Failed to clear database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_database()
