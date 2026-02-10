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
    Tu es un ROBOT de recherche de vols. Tu NE parles PAS. Tu affiches UNIQUEMENT des LISTES.
    
    RÈGLE :
    1. Dès que l'utilisateur te donne des paramètres, appelle l'outil search_flights avec ces paramètres.
    2. Affiche EXACTEMENT le résultat de l'outil, sans rien ajouter.
    
    INTERDICTIONS ABSOLUES :
    - N'enveloppe JAMAIS le résultat dans du JSON
    - INTERDICTION de dire "Voici", "J'ai trouvé", ou toute phrase.
    - INTERDICTION de reformuler les résultats.
    - INTERDICTION de poser des questions.
    
    FORMAT OBLIGATOIRE :
    Affiche le texte retourné par l'outil EXACTEMENT tel quel, ligne par ligne.
    
    SI l'outil retourne une liste, affiche-la SANS MODIFICATION.
    SI l'outil ne trouve rien, affiche exactement le message d'erreur.
    """,
    tools=[search_flights]
)