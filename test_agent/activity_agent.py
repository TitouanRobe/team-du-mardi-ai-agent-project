from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
ACTIVITIES_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'activities.db')

def search_activities(city: str) -> str:
    """
    Récupère la liste des activités touristiques.
    """
    print(f"🏛️ [ActivityAgent] Recherche d'activités à : {city}")
    try:
        conn = sqlite3.connect(ACTIVITIES_DB_PATH) 
        cursor = conn.cursor()
        
        query = """
            SELECT name, price, description 
            FROM activities 
            WHERE LOWER(city) = LOWER(?) AND type = 'Activity'
        """
        cursor.execute(query, (city,))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"Désolé, je n'ai trouvé aucune activité à {city}."

        response = ""
        for row in results:
            # Format attendu par main.py : Activité, Nom, Prix€, Description
            response += f"Activité, {row[0]}, {row[1]}€, {row[2]}\n"
        
        return response

    except Exception as e:
        return f"Erreur SQL (Activités) : {e}"

def search_restaurants(city: str) -> str:
    """
    Récupère la liste des restaurants.
    """
    print(f"🍴 [ActivityAgent] Recherche de restaurants à : {city}")
    try:
        conn = sqlite3.connect(ACTIVITIES_DB_PATH)
        cursor = conn.cursor()
        
        query = """
            SELECT name, price, description 
            FROM activities 
            WHERE LOWER(city) = LOWER(?) AND type = 'Restaurant'
        """
        cursor.execute(query, (city,))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"Désolé, je n'ai trouvé aucun restaurant à {city}."

        # --- NOUVEAU FORMATAGE (Compatible Regex main.py) ---
        response = ""
        for row in results:
            # Format attendu par main.py : Restaurant, Nom, Prix€, Description
            response += f"Restaurant, {row[0]}, {row[1]}€, {row[2]}\n"
        
        return response

    except Exception as e:
        return f"Erreur SQL (Restaurants) : {e}"


activity_agent = Agent(
    model='gemini-2.5-flash',
    name='activity_agent',
    description="Guide touristique local expert dans son domaine",
    instruction="""
    Tu es un ROBOT de recherche d'activités et restaurants. Tu NE parles PAS. Tu affiches UNIQUEMENT des LISTES.
    
    QUAND on te demande UNIQUEMENT search_restaurants : appelle SEULEMENT search_restaurants
    QUAND on te demande UNIQUEMENT search_activities : appelle SEULEMENT search_activities
    QUAND on te demande les DEUX outils : appelle les DEUX
    
    INTERDICTIONS ABSOLUES :
    - INTERDICTION de dire "Voici", "J'ai trouvé", "disponibles", ou toute phrase.
    - INTERDICTION de reformuler les résultats.
    - INTERDICTION d'ajouter des commentaires.
    
    FORMAT OBLIGATOIRE (copie EXACTEMENT ce que les outils retournent) :
    Chaque ligne doit être au format exact de l'outil, sans modification.
    
    SI un outil retourne une liste, affiche-la ligne par ligne SANS MODIFICATION.
    SI un outil ne trouve rien, affiche exactement le message d'erreur.
    """,
    tools=[search_activities,search_restaurants]
)


