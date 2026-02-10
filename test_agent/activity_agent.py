from google.adk.agents.llm_agent import Agent
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVITIES_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'activities.db')


def search_activities(city: str, keyword: str = None) -> str:
    """
    Récupère la liste des activités touristiques.
    Args:
        city: La ville où chercher des activités (ex: Paris, Tokyo, Madrid).
        keyword: Optionnel. Mot-clé pour filtrer (ex: "musée", "parc"). None si non précisé.
    Returns:
        Liste textuelle des activités trouvées.
    """
    print(f"🏛️ [ActivityAgent] Recherche d'activités à : {city} (keyword: {keyword})")
    try:
        conn = sqlite3.connect(ACTIVITIES_DB_PATH)
        cursor = conn.cursor()

        if keyword:
            query = """
                SELECT name, price, description 
                FROM activities 
                WHERE LOWER(city) = LOWER(?) 
                  AND type = 'Activity'
                  AND (LOWER(name) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))
            """
            keyword_pattern = f"%{keyword}%"
            cursor.execute(query, (city, keyword_pattern, keyword_pattern))
        else:
            query = """
                SELECT name, price, description 
                FROM activities 
                WHERE LOWER(city) = LOWER(?) AND type = 'Activity'
            """
            cursor.execute(query, (city,))

        results = cursor.fetchall()
        conn.close()

        if not results:
            keyword_msg = f" avec '{keyword}'" if keyword else ""
            return f"Désolé, je n'ai trouvé aucune activité à {city}{keyword_msg}."

        response = ""
        for row in results:
            response += f"Activité, {row[0]}, {row[1]}€, {row[2]}\n"

        return response

    except Exception as e:
        return f"Erreur SQL (Activités) : {e}"


def search_restaurants(city: str, keyword: str = None) -> str:
    """
    Récupère la liste des restaurants.
    Args:
        city: La ville où chercher des restaurants (ex: Paris, Tokyo, Madrid).
        keyword: Optionnel. Mot-clé pour filtrer (ex: "vegan", "tapas", "italien"). None si non précisé.
    Returns:
        Liste textuelle des restaurants trouvés.
    """
    print(f"🍴 [ActivityAgent] Recherche de restaurants à : {city} (keyword: {keyword})")
    try:
        conn = sqlite3.connect(ACTIVITIES_DB_PATH)
        cursor = conn.cursor()

        if keyword:
            query = """
                SELECT name, price, description 
                FROM activities 
                WHERE LOWER(city) = LOWER(?) 
                  AND type = 'Restaurant'
                  AND (LOWER(name) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))
            """
            keyword_pattern = f"%{keyword}%"
            cursor.execute(query, (city, keyword_pattern, keyword_pattern))
        else:
            query = """
                SELECT name, price, description 
                FROM activities 
                WHERE LOWER(city) = LOWER(?) AND type = 'Restaurant'
            """
            cursor.execute(query, (city,))

        results = cursor.fetchall()
        conn.close()

        if not results:
            keyword_msg = f" avec '{keyword}'" if keyword else ""
            return f"Désolé, je n'ai trouvé aucun restaurant à {city}{keyword_msg}."

        response = ""
        for row in results:
            response += f"Restaurant, {row[0]}, {row[1]}€, {row[2]}\n"

        return response

    except Exception as e:
        return f"Erreur SQL (Restaurants) : {e}"


activity_agent = Agent(
    model='gemini-2.0-flash',
    name='activity_agent',
    description="Guide touristique expert. Utilise search_activities et search_restaurants pour trouver des activités et restaurants dans une ville.",
    instruction="""
    Tu es un agent de recherche d'activités et restaurants.
    
    COMPORTEMENT OBLIGATOIRE :
    Dès que tu reçois une demande mentionnant un voyage ou une ville, tu DOIS immédiatement appeler les DEUX outils :
    1. search_activities(city) pour les activités touristiques
    2. search_restaurants(city) pour les restaurants
    
    - Extrais la ville de destination du message.
    - Si des préférences sont mentionnées (ex: "vegan", "musée"), utilise le paramètre keyword.
    - Si aucune préférence n'est mentionnée, appelle les outils SANS keyword.
    
    Après avoir reçu les résultats, retourne-les EXACTEMENT tels quels, sans modification.
    Affiche d'abord les activités, puis les restaurants, chacun sur une ligne.
    
    INTERDICTIONS :
    - Ne pose JAMAIS de questions.
    - Ne reformule PAS les résultats.
    - N'ajoute PAS de commentaires ou phrases d'introduction.
    """,
    tools=[search_activities, search_restaurants]
)