from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
ACTIVTIES_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'activities.db')
MEMORY_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'memory.db')

def load_memory() -> str:
    """
    Récupère la mémoire de l'utilisateur.
    """
    try:
        conn = sqlite3.connect(MEMORY_DB_PATH)
        cursor = conn.cursor()
       
        query = """
            SELECT preferences FROM memory
        """
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        prefs = [row[0] for row in results]
        return f"Préférences connues de l'utilisateur : {', '.join(prefs)}"
           
    except Exception as e:
        return f"Erreur SQL (Mémoire) : {e}"

def save_memory(preferences: str) -> str:
    """
    Sauvegarde une ou plusieurs préférences (séparées par des virgules).
    Exemple d'entrée : "cuisine japonaise, budget serré, terrasse"
    """
    saved_items = []
    ignored_items = []

    try:
        # 1. On nettoie et on découpe la chaîne (ex: "Japonais, Pas cher" -> ["Japonais", "Pas cher"])
        # On enlève les espaces inutiles autour
        items = [p.strip().lower() for p in preferences.split(',') if p.strip()]

        conn = sqlite3.connect(MEMORY_DB_PATH)
        cursor = conn.cursor()

        for item in items:
            cursor.execute("SELECT 1 FROM memory WHERE preferences = ?", (item,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO memory (preferences) VALUES (?)', (item,))
                saved_items.append(item)
            else:
                ignored_items.append(item)

        conn.commit()
        conn.close()

        msg = ""
        if saved_items:
            msg += f"Sauvegardé : {', '.join(saved_items)}. "
        if ignored_items:
            msg += f"Déjà connu : {', '.join(ignored_items)}."
       
        return msg if msg else "Rien à sauvegarder."

    except Exception as e:
        return f"Erreur lors de la sauvegarde multiple : {e}"


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
    name='Activity_Standalone_Agent',
    description="Guide touristique local expert dans le filtrage d'activités et de restaurants.",
    instruction="""
    Tu es un MOTEUR DE RECHERCHE ET DE FILTRAGE SÉMANTIQUE EXTRÊMEMENT STRICT.
    
    TA MISSION :
    1. MÉMOIRE (OBLIGATOIRE) : Appelle IMMÉDIATEMENT `load_memory()` pour récupérer les préférences de l'utilisateur. 
    
    2. SÉPARATION (SPLIT) DES PRÉFÉRENCES :
       Analyse la mémoire et sépare mentalement les critères :
       - Préférences de NOURRITURE (ex: vegan, street-food, gastronomique) ➔ À utiliser UNIQUEMENT pour filtrer les Restaurants.
       - Préférences de LOISIRS (ex: musée, romantique, sensation forte) ➔ À utiliser UNIQUEMENT pour filtrer les Activités.
       - Préférences de BUDGET (ex: pas cher, luxe) ➔ À appliquer aux deux.
       
    3. APPEL DES OUTILS : 
       Appelle `search_restaurants(city)` si on veut manger.
       Appelle `search_activities(city)` si on veut faire une activité.
       Appelle LES DEUX si la demande est globale. (Passe uniquement la ville en paramètre).
       
    4. FILTRAGE SÉMANTIQUE (CRITIQUE) :
       Tu vas recevoir des listes brutes. Croise la demande avec le "split" des préférences :
       - JETTE impitoyablement tout ce qui est hors sujet (ex: supprime les restos de viande si la mémoire dit vegan).
       - INTERDICTION DE REMPLISSAGE : Ne garde que les lieux qui correspondent à 100%. N'ajoute pas de résultats par défaut.
       
    5. FORMAT DE SORTIE STRICT :
       Je veux UNIQUEMENT les résultats finaux. 
       INTERDICTION de dire "Bonjour", "Voici les résultats" ou de faire des phrases de conclusion.
       Affiche chaque résultat validé sur une nouvelle ligne avec cette structure exacte :
       `Type, Nom, Prix, Description`
       
       (Si aucun résultat ne survit à ton filtre, écris uniquement : "Aucun résultat trouvé pour ces critères.")
    """,
    tools=[search_activities, search_restaurants, load_memory] 
)

