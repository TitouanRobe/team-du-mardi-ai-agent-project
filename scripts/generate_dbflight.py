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
            arrival_time TEXT,
            price REAL,
            airline TEXT,
            flight_number TEXT
        )
    ''')
    
    cursor.execute("DELETE FROM flights")
    
    for _ in range(100): # On augmente un peu pour avoir plus de chances de trouver
        origin, dest = random.sample(CITIES, 2)
        # Date de départ
        dept_date = datetime(2026, 3, 1) + timedelta(days=random.randint(0, 60), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        # Date d'arrivée (entre 2h et 12h plus tard)
        arr_date = dept_date + timedelta(hours=random.randint(2, 12))
        
        flight_no = f"{random.choice(['AF', 'NH', 'DL', 'LH'])}{random.randint(100, 999)}"
        
        cursor.execute('''
            INSERT INTO flights (origin, destination, departure_time, arrival_time, price, airline, flight_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (origin, dest, dept_date.strftime("%Y-%m-%d %H:%M"), arr_date.strftime("%Y-%m-%d %H:%M"), 
              random.randint(350, 1400), random.choice(AIRLINES), flight_no))
    
    conn.commit()
    conn.close()
    print(f"✅ flights.db mis à jour avec 100 vols (départs et arrivées).")

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
            available_start DATE,
            available_end DATE
        )
    ''')
    
    cursor.execute("DELETE FROM hotels") # Reset
    
    types = ["Hotel Resort", "Boutique Hotel", "Business Center", "Luxury Suites", "Budget Inn"]
    for _ in range(60):
        city = random.choice(CITIES)
        hotel_name = f"{city} {random.choice(types)} {random.randint(1, 100)}"
        amenities_str = ", ".join(random.sample(AMENITIES, k=random.randint(2, 4)))
        # Dates aléatoires : début entre mars et août 2026
        start = datetime(2026, random.randint(3, 8), random.randint(1, 28))
        # Fin entre 5 et 30 jours après le début
        end = start + timedelta(days=random.randint(5, 30))
        cursor.execute('''
            INSERT INTO hotels (city, name, price, amenities, available_start, available_end)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (city, hotel_name, random.randint(60, 500), amenities_str, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    
    conn.commit()
    conn.close()
    print(f"hotels.db créé avec 60 hôtels.")

def create_activities_db():
    print("Génération des activités & restaurants (depuis JSON)...")
    
    # 1. Chargement du JSON
    data = load_json_data()
    if not data:
        print("Erreur : Impossible de lire data.json")
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

def create_memory_db():
    db_path = os.path.join(DATA_DIR, 'memory.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preferences TEXT
        )
    ''')
    
    cursor.execute("DELETE FROM memory")
    conn.commit()
    conn.close()
    print(f"memory.db crées.")

if __name__ == "__main__":
    create_flights_db()
    create_hotels_db()
    print("on crée activité")
    create_activities_db()
    create_memory_db()
    print("carré")