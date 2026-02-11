from google.adk.agents.llm_agent import Agent
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHTS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'flights.db')


def search_flights(origin: str, destination: str = None, preferred_date: str = None,
                   max_price: float = None, preferred_airline: str = None) -> str:
    """
    Recherche des vols dans la base de données.
    Args:
        origin: Ville de départ (ex: Paris, Berlin).
        destination: Ville d'arrivée (ex: Tokyo, Madrid). Optionnel.
        preferred_date: Date souhaitée au format YYYY-MM-DD. Optionnel.
        max_price: Budget maximum en euros. Optionnel.
        preferred_airline: Compagnie aérienne préférée. Optionnel.
    Returns:
        Liste textuelle des vols trouvés.
    """
    # --- NETTOYAGE DES PARAMÈTRES ---
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
            query += " AND departure_time >= ?"
            params.append(f"{preferred_date}")

        if max_price:
            query += " AND price <= ?"
            params.append(max_price)

        if preferred_airline:
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
    description="Expert en recherche de vols. Utilise l'outil search_flights pour trouver des vols selon origin, destination, date, budget et compagnie.",
    instruction="""
    Tu es un agent de recherche de vols.
    
    COMPORTEMENT OBLIGATOIRE :
    Dès que tu reçois une demande mentionnant un voyage, un trajet, ou des villes, tu DOIS immédiatement appeler search_flights.
    
    - Extrais "origin" et "destination" du message (les villes mentionnées).
    - Si un budget est mentionné, utilise max_price.
    - Si une date est mentionnée, utilise preferred_date.
    - Si une compagnie est mentionnée, utilise preferred_airline.
    - Si un paramètre n'est pas mentionné, NE le passe PAS à l'outil.
    
    Après avoir reçu le résultat de search_flights, retourne le résultat EXACTEMENT tel quel, sans modification.
    
    INTERDICTIONS :
    - Ne pose JAMAIS de questions.
    - Ne reformule PAS les résultats.
    - N'ajoute PAS de commentaires ou phrases d'introduction.
    """,
    tools=[search_flights]
)