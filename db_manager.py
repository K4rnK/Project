import sqlite3
import pandas as pd
from pathlib import Path

# Set up data directory path
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "real_estate_history.db"

def get_connection():
    """Establish connection to SQLite database in the /data folder."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and default historical records inside /data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                typology TEXT NOT NULL,
                pop_density REAL NOT NULL,
                aadt REAL NOT NULL,
                frontage_m REAL NOT NULL,
                holding_years INTEGER NOT NULL,
                total_value_growth_pct REAL NOT NULL,
                annualized_growth_pct REAL NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM historical_projects")
        if cursor.fetchone()[0] == 0:
            seed_data = [
                # Detached House Projects
                ("Grand Bangkok Boulevard Ratchaphruek", "Detached House Project (โครงการบ้านเดี่ยว)", 3800, 36000, 28, 5, 32.0, 5.71, 13.90, 100.52),
                ("Centro Chaiyapruek-345", "Detached House Project (โครงการบ้านเดี่ยว)", 5200, 48000, 35, 4, 24.0, 5.53, 13.92, 100.55),
                ("Setthasiri Krungthep Kreetha", "Detached House Project (โครงการบ้านเดี่ยว)", 4200, 41000, 30, 5, 35.5, 6.26, 13.75, 100.65),
                
                # Townhome Projects
                ("Pleno Ratchaphruek-346", "Townhome Project (โครงการทาวน์โฮม)", 4900, 42000, 25, 3, 18.5, 5.82, 13.98, 100.51),
                ("Baan Puri Puri Pattanakarn", "Townhome Project (โครงการทาวน์โฮม)", 6100, 51000, 22, 4, 26.0, 5.95, 13.73, 100.62),

                # Community Mall Projects
                ("The Crystal Chaiyapruek", "Community Mall (คอมมูนิตี้มอลล์)", 4500, 55000, 60, 5, 38.0, 6.65, 13.95, 100.60),
                ("Robinsons Lifestyle Ratchaphruek", "Community Mall (คอมมูนิตี้มอลล์)", 5800, 62000, 75, 4, 31.0, 6.98, 13.93, 100.47),

                # Roadside Commercial Shops
                ("Shophouse Corridor 345", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 4800, 52000, 30, 4, 29.0, 6.57, 13.91, 100.58),
                ("Market Place Krungthep Kreetha", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 5100, 58000, 35, 3, 21.5, 6.71, 13.74, 100.64)
            ]
            cursor.executemany('''
                INSERT INTO historical_projects 
                (project_name, typology, pop_density, aadt, frontage_m, holding_years, total_value_growth_pct, annualized_growth_pct, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', seed_data)
        conn.commit()

def fetch_historical_projects(typology=None):
    """Retrieve historical dataset for backtesting analysis."""
    init_db()
    with get_connection() as conn:
        if typology:
            query = "SELECT * FROM historical_projects WHERE typology = ?"
            return pd.read_sql_query(query, conn, params=(typology,))
        else:
            query = "SELECT * FROM historical_projects"
            return pd.read_sql_query(query, conn)

def add_historical_project(name, typology, pop_density, aadt, frontage_m, holding_years, total_growth, lat=13.90, lon=100.50):
    """Insert new backend historical project data into the database in /data."""
    init_db()
    annualized = ((1 + total_growth / 100.0) ** (1.0 / holding_years) - 1) * 100
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historical_projects 
            (project_name, typology, pop_density, aadt, frontage_m, holding_years, total_value_growth_pct, annualized_growth_pct, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, typology, pop_density, aadt, frontage_m, holding_years, total_growth, round(annualized, 2), lat, lon))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized in directory: {DB_FILE}")
