from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
ACTIVTIES_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'activities.db')

def search_activities(city: str) -> str:
    """
    Récupère la liste des activités touristiques.
    """
    try:
        conn = sqlite3.connect(ACTIVTIES_DB_PATH) 
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

        response = f"J'ai trouvé {len(results)} activités disponibles à {city} :\n"
        for row in results:
            response += f"- {row[0]} pour {row[1]}€ (Info : {row[2]})\n"
        
        return response

    except Exception as e:
        return f"Erreur SQL (Activités) : {e}"

def search_restaurants(city: str) -> str:
    """
    Récupère la liste des restaurants.
    """
    try:
        conn = sqlite3.connect(ACTIVTIES_DB_PATH)
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

        # --- NOUVEAU FORMATAGE (Style Hotel) ---
        response = f"J'ai trouvé {len(results)} restaurants disponibles à {city} :\n"
        for row in results:
            # row[0]=name, row[1]=price, row[2]=description
            response += f"- {row[0]} pour {row[1]}€ (Cuisine : {row[2]})\n"
        
        return response

    except Exception as e:
        return f"Erreur SQL (Restaurants) : {e}"


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description="Guide touristique local expert dans son domaine",
    instruction="Tu est un guide local expert et passioné, ta mission est de conseiller l'utilisateur sur quoi faire et ou manger en fonction de ses préférences " \
    "Quand on te demande un RESTAURANT tu DOIS utiliser l'outil search_restaurant" \
    "Quand on te demande une ACTIVITEE tu DOIS utiliser l'outil search_activities" \
    "SI on te demande les DEUX tu DOIS utiliser les DEUX outils, dans ton processus de réflexion" \
    "Je voudrais que tu me donne uniquement les résultat en format type(activité ou restaurant), nom, prix et description pas de discussion en plus",
    tools=[search_activities,search_restaurants]
)


