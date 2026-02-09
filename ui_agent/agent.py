from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
import sqlite3
import os
from typing import List, Tuple, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHTS_DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'flights.db')

def search_flights(origin: str, destination: str) -> List[Tuple]:
    """
    Recherche les vols dans la base de données.
    
    Args:
        origin: La ville de départ (ex: Paris).
        destination: La ville d'arrivée (ex: Tokyo).
        
    Returns:
        Une liste textuelle des vols trouvés (Compagnie, Heure, Prix).
    """
    conn = sqlite3.connect(FLIGHTS_DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT airline, departure_time, price 
        FROM flights 
        WHERE LOWER(origin) = LOWER(?) AND LOWER(destination) = LOWER(?)
        ORDER BY price ASC
    """
    cursor.execute(query, (origin, destination))
    results = cursor.fetchall()
    conn.close()
    return results

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='root_agent',
    description='Donne moi un vol entre deux destinations demandée',
    instruction="tu est agent d'aéroport et des gens vienent te demander des vols d'avions entre deux destinations à une date précise. " \
    "tu dois leur donner un vol entre ces deux destination en utilisant la fonction search_flights." \
    "Il est impératif que les vols soit entre les deux destinations et SURTOUT qu'il soit à la bonne date !" \
    "Quand tu réfléchi, affiche moi un message à chaque phase de ta réflexion, par exemple 'Je choisis les donnée' ",
    tools=[search_flights],
)

# ... (Tout le début est identique : imports, fonctions, définition de l'agent, runner)

if __name__ == "__main__":
    my_runner = Runner(agent=root_agent)
    print("\n✈️  L'Agent est prêt ! (Tape 'quit' pour sortir)")

    while True:
        user_input = input("\n👤 Vous : ")
        if user_input.lower() in ['quit', 'exit']: break
        
        print("") # Petit saut de ligne pour la propreté

        # On lance le Runner, mais on ne stocke pas le résultat tout de suite.
        # On va inspecter ce qui sort en temps réel.
        try:
            # Note : Assure-toi que ta version de Runner supporte run(stream=True)
            # Si ce n'est pas le cas, on devra utiliser une méthode différente.
            response = my_runner.run(user_input, stream=True)
            
            for chunk in response:
                
                # CAS 1 : C'est une ACTION (Reasoning / Tool Use)
                # L'agent veut utiliser ta fonction search_flights
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for call in chunk.tool_calls:
                        # On affiche ça comme un "log système"
                        print(f"\033[93m⚙️  [Système] Je consulte la base de données...")
                        print(f"    Action : {call.name} avec les paramètres {call.args}\033[0m")
                
                # CAS 2 : C'est une PENSÉE INTERNE (Thought)
                # (Certains modèles renvoient leur monologue intérieur ici)
                elif hasattr(chunk, 'thought') and chunk.thought:
                    print(f"\033[90m💭 [Pensée] {chunk.thought}\033[0m")

                # CAS 3 : C'est la RÉPONSE FINALE (Text)
                # C'est ce que l'utilisateur veut lire
                elif chunk.text:
                    print(chunk.text, end="", flush=True)
            
            print("") # Saut de ligne final

        except Exception as e:
            print(f"❌ Erreur : {e}")
