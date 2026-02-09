import sqlite3
import os
from typing import List, Tuple, Optional, Set

# Configuration des chemins robustes
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHTS_DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'flights.db')
HOTELS_DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'hotels.db')


def get_flights_between(origin: str, destination: str) -> List[Tuple]:
    """
    Récupère tous les vols disponibles entre deux villes spécifiques.
    """
    conn = sqlite3.connect(FLIGHTS_DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT airline, departure_time, price 
        FROM flights 
        WHERE LOWER(origin) = LOWER(?) AND LOWER(destination) = LOWER(?)
        ORDER BY price ASC
    """
    cursor.execute(query, (origin, destination))
    results = cursor.fetchall()
    conn.close()
    return results

def get_top_3_cheapest_destinations() -> List[Tuple]:
    """
    Trouve les 3 destinations les moins chères, en prenant le prix minimum 
    disponible pour chaque ville.
    
    Returns:
        List[Tuple]: (Destination, Prix, Compagnie)
    """
    conn = sqlite3.connect(FLIGHTS_DB_PATH)
    cursor = conn.cursor()
    
    # On cherche le prix min par destination pour avoir 3 villes distinctes
    query = """
        SELECT destination, MIN(price) as min_price, airline 
        FROM flights 
        GROUP BY destination 
        ORDER BY min_price ASC 
        LIMIT 3
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

def get_top_5_cheapest_airlines() -> List[Tuple]:
    """
    Calcule le top 5 des compagnies aériennes les moins chères en moyenne.
    """
    conn = sqlite3.connect(FLIGHTS_DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT airline, ROUND(AVG(price), 2) as avg_price 
        FROM flights 
        GROUP BY airline 
        ORDER BY avg_price ASC 
        LIMIT 5
    """
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

def get_hotels_by_comfort(city: str, min_amenities: int = 3) -> List[Tuple]:
    """
    Trouve les hôtels dans une ville qui offrent au moins X services (WiFi, Spa, etc.).
    Utile pour les clients exigeants.
    """
    conn = sqlite3.connect(HOTELS_DB_PATH)
    cursor = conn.cursor()
    # On compte les virgules pour estimer le nombre de services
    query = """
        SELECT name, price, amenities 
        FROM hotels 
        WHERE LOWER(city) = LOWER(?) 
        AND (LENGTH(amenities) - LENGTH(REPLACE(amenities, ',', '')) + 1) >= ?
        ORDER BY price ASC
    """
    cursor.execute(query, (city, min_amenities))
    results = cursor.fetchall()
    conn.close()
    return results

def get_best_value_stay() -> List[Tuple]:
    """
    Le "Coup de Coeur" : Trouve l'hôtel le moins cher parmi ceux qui ont 
    le plus de services (Spa ET Piscine ET Vue sur mer).
    """
    conn = sqlite3.connect(HOTELS_DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT name, city, price, amenities 
        FROM hotels 
        WHERE amenities LIKE '%Spa%' 
        AND amenities LIKE '%Piscine%' 
        AND amenities LIKE '%Vue sur mer%'
        ORDER BY price ASC 
        LIMIT 1
    """
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_available_amenities(city: str) -> Set[str]:
    """
    Scanne tous les hôtels d'une ville pour lister les services existants.
    
    Args:
        city (str): La ville à scanner.
    Returns:
        Set[str]: Un ensemble (unique) de tous les services disponibles (ex: {'WiFi', 'Spa'}).
    """
    conn = sqlite3.connect(HOTELS_DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT amenities FROM hotels WHERE LOWER(city) = LOWER(?)"
    cursor.execute(query, (city,))
    rows = cursor.fetchall()
    conn.close()

    # On transforme les chaînes "WiFi, Spa" en une liste unique propre
    all_amenities = set()
    for row in rows:
        # row[0] ressemble à "WiFi, Spa, Piscine"
        services = [s.strip() for s in row[0].split(',')]
        all_amenities.update(services)
    
    return all_amenities

def search_hotels_by_multiple_amenities(city: str, amenities_list: List[str]) -> List[Tuple]:
    """
    Filtre les hôtels qui possèdent TOUS les services demandés.
    
    Args:
        city (str): La ville de recherche.
        amenities_list (List[str]): Liste des services (ex: ['WiFi', 'Piscine']).
    """
    conn = sqlite3.connect(HOTELS_DB_PATH)
    cursor = conn.cursor()
    
    # On commence la requête de base
    query = "SELECT name, price, amenities FROM hotels WHERE LOWER(city) = LOWER(?)"
    params = [city]
    
    # On ajoute une condition "AND amenities LIKE ?" pour chaque service
    for amenity in amenities_list:
        query += " AND amenities LIKE ?"
        params.append(f"%{amenity.strip()}%")
    
    query += " ORDER BY price ASC"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

# --- LE MAIN INTERACTIF ---
if __name__ == "__main__":
    print("BIENVENUE SUR TRAVELAGENT.AI\n")

    # 1. Recherche par villes
    ville_dep = "Tokyo"
    ville_arr = "Berlin"
    
    vols = get_flights_between(ville_dep, ville_arr)
    if vols:
        print(f"\nVols trouvés pour {ville_dep} -> {ville_arr} :")
        for v in vols:
            print(f"   - {v[0]} | {v[1]} | {v[2]}€")
    else:
        print(f"\nAucun vol trouvé pour ce trajet.")

    # 2. La destination la moins chère
    print("\nTOP 3 DES DESTINATIONS LES MOINS CHÈRES :")
    top_3 = get_top_3_cheapest_destinations()
    for i, (dest, prix, air) in enumerate(top_3, 1):
        print(f"   {i}. {dest} dès {prix}€ avec {air}")

    # 3. Top 5 compagnies
    print("\nTop 5 des compagnies les moins chères (moyenne) :")
    top_compagnies = get_top_5_cheapest_airlines()
    for i, comp in enumerate(top_compagnies, 1):
        print(f"   {i}. {comp[0]} ({comp[1]}€ en moyenne)")

    print(" ANALYSE DES HÔTELS \n")

    ville = "Tokyo"

    # 2. Test Confort
    print(f"\nHôtels haut de gamme à {ville} (3+ services) :")
    comfort_stays = get_hotels_by_comfort(ville, 3)
    for name, price, am in comfort_stays[:3]: # On en montre 3 max
        print(f"  {name} ({price}€) -> {am}")

    # 3. Le Best Value
    print("\nLE MEILLEUR RAPPORT PRESTATION/PRIX :")
    best = get_best_value_stay()
    if best:
        h = best[0]
        print(f"  {h[0]} à {h[1]} pour {h[2]}€ seulement !")

    
    print("🌍 --- RECHERCHE MULTI-CRITÈRES --- 🌍\n")

    city_input = input("📍 Ville : ")
    
    available = get_all_available_amenities(city_input)
    print(f"✨ Services à {city_input} : {', '.join(available)}")
    
    raw_choices = input("\n🔍 Entrez vos services (séparez par une virgule) : ")
    choices_list = [c.strip() for c in raw_choices.split(',') if c.strip()]
    
    matches = search_hotels_by_multiple_amenities(city_input, choices_list)
    
    if matches:
        print(f"\n✅ {len(matches)} hôtels correspondent à vos critères ({', '.join(choices_list)}) :")
        for name, price, am in matches:
            print(f"   - {name} ({price}€/nuit) | {am}")
    else:
        print(f"\n❌ Aucun hôtel ne réunit TOUS ces critères à {city_input}.")

    

