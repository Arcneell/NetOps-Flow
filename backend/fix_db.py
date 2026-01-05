from sqlalchemy import text
from backend.core.database import engine

def fix():
    with engine.connect() as conn:
        print("Attempting to add task_id column to script_executions...")
        try:
            # Postgres 9.6+ supports IF NOT EXISTS for columns
            conn.execute(text("ALTER TABLE script_executions ADD COLUMN IF NOT EXISTS task_id VARCHAR"))
            conn.commit()
            print("Success: Column 'task_id' checked/added.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    fix()
