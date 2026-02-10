from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

# 1. Calcul dynamique du chemin pour trouver la DB peu importe d'où on lance le script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
# On remonte d'un cran (..) pour aller dans data
HOTELS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'hotels.db')


def search_hotels(city: str, budget: float = 1000000, amenities: str = None,
                  date_start: str = None, date_end: str = None) -> str:
    """
    Recherche les hotels dans la base de données.
    Args:
        city: La ville où chercher un hotel (ex: Paris, Tokyo).
        budget: Optionnel. Le budget maximum en euros (ex: 150.0). Par défaut 1000000 (pas de limite).
        amenities: Optionnel. Les services souhaités (ex: "WiFi, Spa"). None si non précisé.
        date_start: Optionnel. Date de début du séjour au format YYYY-MM-DD (ex: "2026-04-10"). None si non précisé.
        date_end: Optionnel. Date de fin du séjour au format YYYY-MM-DD (ex: "2026-04-15"). None si non précisé.

    Returns:
        Une liste textuelle des hotels trouvés.
    """
    print(f"\n [DEBUG] Recherche : {city}, budget={budget}€, amenities={amenities}, dates={date_start} -> {date_end}")

    try:
        if not os.path.exists(HOTELS_DB_PATH):
            return f"ERREUR: Le fichier database est introuvable ici : {HOTELS_DB_PATH}"

        conn = sqlite3.connect(HOTELS_DB_PATH)
        cursor = conn.cursor()

        # requête
        query = """
                SELECT city, name, price, amenities, available_start, available_end 
                FROM hotels WHERE city LIKE ? AND price <= ?
                """
        params = [f"%{city}%", budget]

        if amenities is not None:
            query += " AND amenities LIKE ?"
            params.append(f"%{amenities}%")

        # si ajout des deux dates
        if date_start and date_end:
            query += " AND available_start <= ? AND available_end >= ?"
            params.extend([date_start, date_end])

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        print(f"Résultats trouvés : {results}")

        if not results:
            return f"Désolé, je n'ai trouvé aucun hotel dans la base de données pour {city}."

        response = ""
        for r in results:
            # r[0]=city, r[1]=name, r[2]=price, r[3]=amenities, r[4]=available_start, r[5]=available_end
            response += f"- {r[1]} à {r[0]} pour {r[2]}€/nuit (Dispo: {r[4]} au {r[5]}, Services: {r[3]})\n"

        return response

    except Exception as e:
        print(f"Erreur SQL : {e}")
        return f"Erreur technique lors de la recherche : {e}"


# Définition de l'agent
hotel_agent = Agent(
    model='gemini-2.5-flash',
    name='hotel_agent',
    description='Expert en recherche en hotels.',
    instruction="""
    Tu es un ROBOT de recherche d'hôtels. Tu NE parles PAS. Tu affiches UNIQUEMENT des LISTES.
    
    QUAND on te demande des hôtels, utilise l'outil search_hotels.
    
    INTERDICTIONS ABSOLUES :
    - INTERDICTION de dire "Voici", "J'ai trouvé", "disponibles", ou toute phrase.
    - INTERDICTION de reformuler les résultats.
    - INTERDICTION d'ajouter des commentaires.
    
    FORMAT OBLIGATOIRE (copie EXACTEMENT ce que l'outil retourne) :
    Chaque ligne doit commencer par "- " suivi du format exact de l'outil.
    
    SI l'outil retourne une liste, affiche-la ligne par ligne SANS MODIFICATION.
    SI l'outil dit "Aucun hôtel", affiche exactement ce message.
    """,
    tools=[search_hotels]
)