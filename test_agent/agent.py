from google.adk.agents.llm_agent import Agent
def search_flights(origin,dest,date):
    return

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='root_agent',
    description='Donne moi un vole entre deux destinations demandée',
    instruction="tu est agent d'aéroport et des gens vienent te demander des vols d'avions entre deux destinations à une date précise. " \
    "tu dois leur donner un vol entre ces deux destination en utilisant la fonction search_flight au dessus." \
    "Il est impératif que les vols soit entre les deux destinations et SURTOUT qu'il soit à la bonne date !",
)
