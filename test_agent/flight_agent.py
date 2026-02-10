from google.adk.agents.llm_agent import Agent
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHTS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'flights.db')

def search_flights(origin: str, destination: str = None, preferred_date: str = None, 
                   max_price: float = None, preferred_airline: str = None) -> str:
    # --- NETTOYAGE DES PARAMÈTRES ---
    # Si l'IA envoie des mots génériques, on les annule pour le SQL
    if destination and destination.lower() in ["partout", "n'importe où", "anywhere", "none"]:
        destination = None
    if preferred_airline and preferred_airline.lower() in ["n'importe laquelle", "none"]:
        preferred_airline = None

    print(f"✈️ [DEBUG] SQL -> Origin: {origin} | Dest: {destination} | Date: {preferred_date} | Budget: {max_price} | Cie: {preferred_airline}")

    try:
        conn = sqlite3.connect(FLIGHTS_DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT airline, flight_number, origin, destination, departure_time, arrival_time, price FROM flights WHERE origin LIKE ?"
        params = [f"%{origin}%"]

        if destination:
            query += " AND destination LIKE ?"
            params.append(f"%{destination}%")
        
        if preferred_date:
            query += " AND departure_time LIKE ?"
            params.append(f"{preferred_date}%")
            
        if max_price:
            query += " AND price <= ?"
            params.append(max_price)
            
        if preferred_airline:
            # On cherche juste le mot clé (ex: 'Air' pour 'Air France')
            query += " AND airline LIKE ?"
            params.append(f"%{preferred_airline}%")

        query += " ORDER BY price ASC"
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        if not results:
            return "Désolé, aucun vol ne correspond. Modifiez vos filtres (budget, date ou destination)."
        
        resp = f"Voici les vols trouvés au départ de {origin} :\n"
        for r in results:
            resp += f"- {r[0]} ({r[1]}) : {r[2]} -> {r[3]} | départ {r[4]} arrivée {r[5]} pour {r[6]}€\n"
        return resp
    except Exception as e:
        return f"Erreur technique : {e}"

flight_agent = Agent(
    name="FlightAgent",
    model="gemini-2.5-flash", 
    instruction="""
    Tu es un automate de recherche de vols. INTERDICTION de poser des questions si tu as la ville de départ.
    
    RÈGLES D'OR :
    1. Dès que l'utilisateur mentionne une ville de départ, appelle l'outil search_flights.
    2. Si une information manque (destination, date, budget), laisse le paramètre vide (None) ou n'en parle pas.
    3. Si l'utilisateur dit 'Airfrance' ou 'Air france', passe 'Air' à l'outil.
    4. Nous sommes en 2026. Si on te dit 'en mars', envoie '2026-03'.
    5. NE RÉPONDS JAMAIS par une question. Si l'outil ne trouve rien, affiche le message d'erreur de l'outil et propose d'autres villes.
    
    FORMAT :
    - [Compagnie] ([Numéro]) : [Départ] -> [Arrivée] | départ [Date Heure] arrivée [Date Heure] pour [Prix]€
    """,
    tools=[search_flights]
)