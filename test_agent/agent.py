from google.adk.agents.llm_agent import Agent
import sqlite3
import os
from typing import List, Tuple, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHTS_DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'flights.db')

def get_flights_between(origin: str, destination: str) -> List[Tuple]:
    """
    Récupère tous les vols disponibles entre deux villes spécifiques.
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
    model='gemini-2.0-flash-lite',
    name='root_agent',
    description='Donne moi un vol entre deux destinations demandée',
    instruction="tu est agent d'aéroport et des gens vienent te demander des vols d'avions entre deux destinations à une date précise. " \
    "tu dois leur donner un vol entre ces deux destination en utilisant la fonction get_flights_between au dessus." \
    "Il est impératif que les vols soit entre les deux destinations et SURTOUT qu'il soit à la bonne date !",
    tools=[get_flights_between],

)
