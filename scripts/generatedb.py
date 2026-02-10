import sqlite3
import random
import os
from datetime import datetime, timedelta
import json

# Dossier de destination
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Données pour le réalisme
CITIES = ["Paris", "Tokyo", "New York", "Berlin", "London", "Bangkok", "Lisbonne", "Rome", "Madrid", "Sydney"]
AIRLINES = ["Air France", "ANA", "Delta", "Lufthansa", "British Airways", "Emirates", "Japan Airlines", "United"]
AMENITIES = ["WiFi", "Petit-déjeuner inclus", "Piscine", "Spa", "Salle de sport", "Climatisation", "Vue sur mer"]

def load_json_data():
    json_path = '../data/activities.json' # Ou os.path.join(DATA_DIR, 'data.json') selon où tu l'as mis
    if not os.path.exists(json_path):
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
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

def create_activities_db():
    print("🎟️  Génération des activités & restaurants (depuis JSON)...")
    
    # 1. Chargement du JSON
    data = load_json_data()
    if not data:
        print("⚠️  Erreur : Impossible de lire data.json")
        return

    db_path = os.path.join(DATA_DIR, 'activities.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 2. Création de la table avec la colonne 'type'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            type TEXT
        )
    ''')
    
    # 3. Nettoyage de l'ancienne table
    cursor.execute("DELETE FROM activities") # Reset
    
    # 4. Insertion des données depuis le JSON
    count = 0
    for city, city_data in data.items():
        
        # --- TRAITEMENT DES ACTIVITÉS ---
        if "activities" in city_data:
            for activity in city_data["activities"]:
                cursor.execute('''
                    INSERT INTO activities (city, name, description, price, type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (city, activity['name'], activity['description'], activity['price'], 'Activity'))
                count += 1
        
        # --- TRAITEMENT DES RESTAURANTS ---
        if "restaurants" in city_data:
            for resto in city_data["restaurants"]:
                cursor.execute('''
                    INSERT INTO activities (city, name, description, price, type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (city, resto['name'], resto['description'], resto['price'], 'Restaurant'))
                count += 1
    
    conn.commit()
    conn.close()
    print(f"activities.db créé avec {count} entrées (Activités + Restaurants).")
    
if __name__ == "__main__":
    create_flights_db()
    create_hotels_db()
    print("on crée activité")
    create_activities_db()
    print("carré")