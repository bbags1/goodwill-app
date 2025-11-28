import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'gw_data.db')

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Add is_saved column
    try:
        c.execute('ALTER TABLE items ADD COLUMN is_saved BOOLEAN DEFAULT 0')
        print("Added is_saved column")
    except:
        pass
        
    # Add gemini_price column
    try:
        c.execute('ALTER TABLE items ADD COLUMN gemini_price REAL DEFAULT 0')
        print("Added gemini_price column")
    except:
        pass
        
    # Add gemini_analysis column
    try:
        c.execute('ALTER TABLE items ADD COLUMN gemini_analysis TEXT')
        print("Added gemini_analysis column")
    except:
        pass
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_db()

