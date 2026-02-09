from google.adk.agents.llm_agent import Agent
import sqlite3
import os

# 1. Calcul dynamique du chemin pour trouver la DB peu importe d'où on lance le script
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Dossier test_agent
# On remonte d'un cran (..) pour aller dans data
FLIGHTS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'flights.db')

def search_flights(origin: str, destination: str) -> str:
    """
    Recherche les vols dans la DB.
    Utilise LIKE pour être insensible à la casse (Paris = paris).
    """
    print(f"\n🔎 [DEBUG] L'agent appelle l'outil avec : {origin} -> {destination}")
    print(f"📂 [DEBUG] Chemin de la DB utilisé : {FLIGHTS_DB_PATH}")

    try:
        if not os.path.exists(FLIGHTS_DB_PATH):
            return f"ERREUR: Le fichier database est introuvable ici : {FLIGHTS_DB_PATH}"

        conn = sqlite3.connect(FLIGHTS_DB_PATH)
        cursor = conn.cursor()
        
        # 2. On utilise LIKE et des % pour que "paris" trouve "Paris" ou "Paris CDG"
        query = """
            SELECT airline, departure_time, price 
            FROM flights 
            WHERE origin LIKE ? AND destination LIKE ?
        """
        # Les % permettent de chercher "contient ce mot"
        cursor.execute(query, (f"%{origin}%", f"%{destination}%"))
        results = cursor.fetchall()
        conn.close()

        print(f"✅ [DEBUG] Résultats trouvés : {results}")

        if not results:
            return f"Désolé, je n'ai trouvé aucun vol dans la base de données pour {origin} vers {destination}."
        
        # 3. On formate une belle réponse texte pour l'agent
        response = f"J'ai trouvé {len(results)} vols disponibles :\n"
        for r in results:
            # r[0]=airline, r[1]=time, r[2]=price
            response += f"- {r[0]} départ à {r[1]} pour {r[2]}€\n"
            
        return response

    except Exception as e:
        print(f"❌ [DEBUG] Erreur SQL : {e}")
        return f"Erreur technique lors de la recherche : {e}"

# Définition de l'agent
root_agent = Agent(
    model='gemini-2.0-flash', # Ou gemini-1.5-flash
    name='travel_agent',
    description='Expert en recherche de vols.',
    instruction="""
    Tu es un agent de voyage serviable.
    QUAND on te demande un vol, tu DOIS utiliser l'outil search_flights.
    Une fois que l'outil te répond, formule une phrase complète et agréable pour l'utilisateur.
    Ne montre pas de JSON ou de code à l'utilisateur.
    """,
    tools=[search_flights]
)