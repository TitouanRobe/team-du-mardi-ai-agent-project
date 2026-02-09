import sqlite3
import random
import os
from datetime import datetime, timedelta

# Dossier de destination
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Données pour le réalisme
CITIES = ["Paris", "Tokyo", "New York", "Berlin", "London", "Bangkok", "Lisbonne", "Rome", "Madrid", "Sydney"]
AIRLINES = ["Air France", "ANA", "Delta", "Lufthansa", "British Airways", "Emirates", "Japan Airlines", "United"]
AMENITIES = ["WiFi", "Petit-déjeuner inclus", "Piscine", "Spa", "Salle de sport", "Climatisation", "Vue sur mer"]

def create_flights_db():
    db_path = os.path.join(DATA_DIR, 'flights.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            departure_time TEXT,
            price REAL,
            airline TEXT
        )
    ''')
    
    cursor.execute("DELETE FROM flights") # Reset
    
    for _ in range(60):
        origin, dest = random.sample(CITIES, 2)
        date = datetime(2026, 3, 1) + timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
        cursor.execute('''
            INSERT INTO flights (origin, destination, departure_time, price, airline)
            VALUES (?, ?, ?, ?, ?)
        ''', (origin, dest, date.strftime("%Y-%m-%d %H:%M"), random.randint(350, 1400), random.choice(AIRLINES)))
    
    conn.commit()
    conn.close()
    print(f" flights.db créé avec 60 vols.")

def create_hotels_db():
    db_path = os.path.join(DATA_DIR, 'hotels.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            name TEXT,
            price REAL,
            amenities TEXT,
            available_dates TEXT
        )
    ''')
    
    cursor.execute("DELETE FROM hotels") # Reset
    
    types = ["Hotel Resort", "Boutique Hotel", "Business Center", "Luxury Suites", "Budget Inn"]
    for _ in range(60):
        city = random.choice(CITIES)
        hotel_name = f"{city} {random.choice(types)} {random.randint(1, 100)}"
        amenities_str = ", ".join(random.sample(AMENITIES, k=random.randint(2, 4)))
        cursor.execute('''
            INSERT INTO hotels (city, name, price, amenities, available_dates)
            VALUES (?, ?, ?, ?, ?)
        ''', (city, hotel_name, random.randint(60, 500), amenities_str, "2026-03-01 to 2026-05-31"))
    
    conn.commit()
    conn.close()
    print(f"hotels.db créé avec 60 hôtels.")

if __name__ == "__main__":
    create_flights_db()
    create_hotels_db()
    print("carré")