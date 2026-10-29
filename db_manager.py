import sqlite3
import pandas as pd
from pathlib import Path

DB_FILE = Path(__file__).parent / "real_estate_history.db"

def get_connection():
    """Establish connection to SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and default historical records if empty."""
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
        
        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM historical_projects")
        if cursor.fetchone()[0] == 0:
            seed_data = [
                ("Sample D-1", "Detached House Project (โครงการบ้านเดี่ยว)", 3800, 36000, 28, 5, 32.0, 5.71, 13.90, 100.52),
                ("Sample D-2", "Detached House Project (โครงการบ้านเดี่ยว)", 5200, 48000, 35, 4, 24.0, 5.53, 13.92, 100.55),
                ("Sample D-3", "Detached House Project (โครงการบ้านเดี่ยว)", 2600, 22000, 25, 6, 41.0, 5.89, 13.88, 100.48),
                ("Sample D-4", "Detached House Project (โครงการบ้านเดี่ยว)", 6100, 61000, 40, 3, 15.0, 4.77, 13.98, 100.65),
                ("Sample M-1", "Community Mall (คอมมูนิตี้มอลล์)", 4500, 55000, 60, 5, 38.0, 6.65, 13.95, 100.60),
                ("Sample M-2", "Community Mall (คอมมูนิตี้มอลล์)", 3200, 40000, 45, 4, 21.0, 4.88, 13.85, 100.50),
                ("Sample M-3", "Community Mall (คอมมูนิตี้มอลล์)", 6800, 72000, 70, 6, 55.0, 7.58, 14.02, 100.68),
                ("Sample M-4", "Community Mall (คอมมูนิตี้มอลล์)", 2800, 30000, 38, 5, 18.0, 3.37, 13.82, 100.45),
                ("Sample S-1", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 4800, 52000, 30, 4, 29.0, 6.57, 13.91, 100.58),
                ("Sample S-2", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 3500, 38000, 24, 5, 22.0, 4.06, 13.87, 100.51),
                ("Sample S-3", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 6200, 68000, 36, 3, 19.0, 5.97, 13.99, 100.63),
                ("Sample S-4", "Roadside Commercial Shop (อาคารพาณิชย์ริมถนน)", 2900, 28000, 28, 6, 26.0, 3.93, 13.80, 100.42),
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
    """Insert new backend historical project data."""
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
    print("Database initialized successfully.")