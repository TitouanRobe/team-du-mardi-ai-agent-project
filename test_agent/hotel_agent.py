from google.adk.agents.llm_agent import Agent
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOTELS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'hotels.db')


def search_hotels(city: str, budget: float = 1000000, amenities: str = None,
                  date_start: str = None, date_end: str = None) -> str:
    """
    Recherche les hotels dans la base de données.
    Args:
        city: La ville où chercher un hotel (ex: Paris, Tokyo, Madrid).
        budget: Optionnel. Le budget maximum en euros (ex: 150.0). Par défaut 1000000 (pas de limite).
        amenities: Optionnel. Les services souhaités (ex: "WiFi, Spa"). None si non précisé.
        date_start: Optionnel. Date de début du séjour au format YYYY-MM-DD. None si non précisé.
        date_end: Optionnel. Date de fin du séjour au format YYYY-MM-DD. None si non précisé.
    Returns:
        Une liste textuelle des hotels trouvés.
    """
    print(f"\n🏨 [DEBUG] Recherche : {city}, budget={budget}€, amenities={amenities}, dates={date_start} -> {date_end}")

    try:
        if not os.path.exists(HOTELS_DB_PATH):
            return f"ERREUR: Le fichier database est introuvable ici : {HOTELS_DB_PATH}"

        conn = sqlite3.connect(HOTELS_DB_PATH)
        cursor = conn.cursor()

        query = """
                SELECT city, name, price, amenities, available_start, available_end 
                FROM hotels WHERE city LIKE ? AND price <= ?
                """
        params = [f"%{city}%", budget]

        if amenities is not None:
            for amenity in amenities.split(","):
                amenity = amenity.strip()
                if amenity:
                    query += " AND amenities LIKE ?"
                    params.append(f"%{amenity}%")

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
            response += f"- {r[1]} à {r[0]} pour {r[2]}€/nuit (Dispo: {r[4]} au {r[5]}, Services: {r[3]})\n"

        return response

    except Exception as e:
        print(f"Erreur SQL : {e}")
        return f"Erreur technique lors de la recherche : {e}"


hotel_agent = Agent(
    model='gemini-2.0-flash',
    name='hotel_agent',
    description="Expert en recherche d'hôtels. Utilise l'outil search_hotels pour trouver des hôtels selon la ville, le budget et les services.",
    instruction="""
    Tu es un agent de recherche d'hôtels.
    
    COMPORTEMENT OBLIGATOIRE :
    Dès que tu reçois une demande mentionnant un voyage, une ville, ou un hébergement, tu DOIS immédiatement appeler search_hotels.
    
    - Extrais la ville de destination du message.
    - Si un budget hôtel est mentionné, utilise le paramètre budget.
    - Si des services sont mentionnés (Spa, WiFi, Piscine), utilise le paramètre amenities.
    - Si des dates sont mentionnées, utilise date_start et date_end.
    - Si un paramètre n'est pas mentionné, NE le passe PAS à l'outil.
    
    Après avoir reçu le résultat de search_hotels, retourne le résultat EXACTEMENT tel quel, sans modification.
    
    INTERDICTIONS :
    - Ne pose JAMAIS de questions.
    - Ne reformule PAS les résultats.
    - N'ajoute PAS de commentaires ou phrases d'introduction.
    """,
    tools=[search_hotels]
)