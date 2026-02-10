from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

# 1. Calcul dynamique du chemin pour trouver la DB peu importe d'où on lance le script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
# On remonte d'un cran (..) pour aller dans data
HOTELS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'hotels.db')


def search_hotels(city: str, budget: float = 1000000, amenities: str = None) -> str:
    """
    Recherche les hotels dans la base de données.
    Args:
        city: La ville où chercher un hotel (ex: Paris, Tokyo).
        budget: Optionnel. Le budget maximum en euros (ex: 150.0). Par défaut 1000000 (pas de limite).
        amenities: Les services souhaités, séparés par des virgules (ex: "WiFi, Spa").
                   Peut être None si aucun service spécifique n'est demandé.

    Returns:
        Une liste textuelle des hotels trouvés.
    """
    print(f"\n [DEBUG] L'agent appelle l'outil avec : {city} et un budget de {budget}€ et activités : {amenities}")
    print(f" [DEBUG] Chemin de la DB utilisé : {HOTELS_DB_PATH}")

    try:
        if not os.path.exists(HOTELS_DB_PATH):
            return f"ERREUR: Le fichier database est introuvable ici : {HOTELS_DB_PATH}"

        conn = sqlite3.connect(HOTELS_DB_PATH)
        cursor = conn.cursor()

        if amenities is None:
            query = """
                    SELECT city, name, price, amenities, available_dates
                    FROM hotels
                    WHERE city LIKE ? \
                      AND price <= ? \
                    """
            # Les % permettent de chercher "contient ce mot"
            cursor.execute(query, (f"%{city}%", budget))
        else :

            query = """
                    SELECT city, name, price, amenities, available_dates
                    FROM hotels
                    WHERE city LIKE ? \
                      AND price <= ? \
                      AND amenities LIKE ? \
                    """
            # Les % permettent de chercher "contient ce mot"
            cursor.execute(query, (f"%{city}%", budget, f"%{amenities}%"))

        results = cursor.fetchall()
        conn.close()

        print(f"Résultats trouvés : {results}")

        if not results:
            return f"Désolé, je n'ai trouvé aucun hotel dans la base de données pour {city}."

        # 3. On formate une belle réponse texte pour l'agent
        response = f"J'ai trouvé {len(results)} hotels disponibles :\n"
        for r in results:
            # r[0]=city, r[1]=name, r[2]=price, r[3]=amenities, r[4]=available_dates
            response += f"- {r[1]} à {r[0]} pour {r[2]}€ (Dates : {r[4]})\n"

        return response

    except Exception as e:
        print(f"xErreur SQL : {e}")
        return f"Erreur technique lors de la recherche : {e}"


# Définition de l'agent
root_agent = Agent(
    model='gemini-2.5-flash',  # Ou gemini-1.5-flash
    name='hotel_agent',
    description='Expert en recherche en hotels.',
    instruction="""
    Tu es un agent de voyage spécialisé dans l'hôtellerie.
    QUAND on te demande un hotel, utilise l'outil search_hotels.
    Tu as SEULEMENT besoin de la ville pour lancer une recherche.
    Si l'utilisateur précise un budget, passe-le en paramètre. Sinon, ne le précise pas.
    Si l'utilisateur précise des services (amenities), passe-les. Sinon, ne les précise pas.
    Si l'utilisateur ne precise pas de dates (dates), passe-les. Sinon, ne les précise pas.
    Formule une réponse agréable avec les résultats sans intégrer de JSON ou de code.
    """,
    tools=[search_hotels]
)