from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os

# 1. Calcul dynamique du chemin pour trouver la DB peu importe d'où on lance le script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Dossier test_agent
# On remonte d'un cran (..) pour aller dans data
HOTELS_DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'hotels.db')


def search_hotels(city) -> str:
    """
    Recherche les hotels dans la DB.
    Utilise LIKE pour être insensible à la casse (Hotel = hotel).
    """
    print(f"\n🔎 [DEBUG] L'agent appelle l'outil avec : {city}")
    print(f"📂 [DEBUG] Chemin de la DB utilisé : {HOTELS_DB_PATH}")

    try:
        if not os.path.exists(HOTELS_DB_PATH):
            return f"ERREUR: Le fichier database est introuvable ici : {HOTELS_DB_PATH}"

        conn = sqlite3.connect(HOTELS_DB_PATH)
        cursor = conn.cursor()

        # 2. On utilise LIKE et des % pour que "paris" trouve "Paris" ou "Paris CDG"
        query = """
                SELECT city, name, price, amenities, available_dates
                FROM hotels
                WHERE city LIKE ? \
                """
        # Les % permettent de chercher "contient ce mot"
        cursor.execute(query, (f"%{city}%",))
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
    model='gemini-2.0-flash',  # Ou gemini-1.5-flash
    name='hotel_agent',
    description='Expert en recherche en hotels.',
    instruction="""
    Tu es un agent de voyage serviable.
    QUAND on te demande un hotel, tu DOIS utiliser l'outil search_hotel.
    Une fois que l'outil te répond, formule une phrase complète et agréable pour l'utilisateur.
    Ne montre pas de JSON ou de code à l'utilisateur.
    """,
    tools=[search_hotels]
)


if __name__ == "__main__":
    my_runner = Runner(agent=root_agent)
    print("\nL'Agent Hotels est prêt ! (Tape 'quit' pour sortir)")

    while True:
        user_input = input("\n👤 Vous : ")
        if user_input.lower() in ['quit', 'exit']:
            break

        print("")

        try:
            response = my_runner.run(user_input, stream=True)

            for chunk in response:
                # DEBUG: Afficher le type et les attributs du chunk
                print(f"\n\033[94m[DEBUG] Type: {type(chunk).__name__}\033[0m")
                print(f"\033[94m[DEBUG] Attributs: {[a for a in dir(chunk) if not a.startswith('_')]}\033[0m")
                
                # Afficher les valeurs des attributs intéressants
                if hasattr(chunk, 'author'):
                    print(f"\033[93m[DEBUG] author: {chunk.author}\033[0m")
                if hasattr(chunk, 'actions') and chunk.actions:
                    print(f"\033[93m[DEBUG] actions: {chunk.actions}\033[0m")

                # Affichage de la réponse texte
                if hasattr(chunk, 'text') and chunk.text:
                    print(chunk.text, end="", flush=True)

            print("")

        except Exception as e:
            print(f"Erreur : {e}")