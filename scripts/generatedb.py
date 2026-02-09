import json
import random
from datetime import datetime, timedelta

# Listes de données pour le réalisme
CITIES = ["Paris", "Tokyo", "New York", "Berlin", "London", "Bangkok", "Lisbonne", "Rome", "Madrid", "Sydney"]
AIRLINES = ["Air France", "ANA", "Delta", "Lufthansa", "British Airways", "Emirates", "Japan Airlines", "United"]
AMENITIES = ["WiFi", "Petit-déjeuner inclus", "Piscine", "Spa", "Salle de sport", "Climatisation", "Vue sur mer"]

def generate_flights(count=60):
    flights = []
    for i in range(count):
        origin, dest = random.sample(CITIES, 2)
        # Dates en 2026
        date = datetime(2026, 3, 1) + timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
        flights.append({
            "id": i + 1,
            "origin": origin,
            "destination": dest,
            "departure_time": date.strftime("%Y-%m-%d %H:%M"),
            "price": random.randint(350, 1400),
            "airline": random.choice(AIRLINES)
        })
    return flights

def generate_hotels(count=60):
    hotels = []
    types = ["Hotel Resort", "Boutique Hotel", "Business Center", "Luxury Suites", "Budget Inn"]
    for i in range(count):
        city = random.choice(CITIES)
        hotels.append({
            "id": i + 1,
            "city": city,
            "name": f"{city} {random.choice(types)} {random.randint(1, 100)}",
            "price_per_night": random.randint(60, 500),
            "amenities": random.sample(AMENITIES, k=random.randint(2, 4)),
            "available_dates": ["2026-03-01", "2026-05-31"]
        })
    return hotels

if __name__ == "__main__":
    # Création du dossier data s'il n'existe pas
    import os
    if not os.path.exists('data'): os.makedirs('data')

    with open('data/flights.json', 'w', encoding='utf-8') as f:
        json.dump(generate_flights(60), f, indent=4, ensure_ascii=False)
    
    with open('data/hotels.json', 'w', encoding='utf-8') as f:
        json.dump(generate_hotels(60), f, indent=4, ensure_ascii=False)

    print(f"✅ Succès : data/flights.json (60 entrées) et data/hotels.json (60 entrées) créés.")