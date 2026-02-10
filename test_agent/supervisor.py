from google.adk.agents.llm_agent import Agent
# On importe les agents spécialisés depuis les autres fichiers du dossier
from .flight_agent import flight_agent
from .hotel_agent import hotel_agent
from .activity_agent import activity_agent

# Le Supervisor est l'agent "root" que main.py va appeler
root_agent = Agent(
    model='gemini-2.0-flash',
    name='Travel_Supervisor',
    description='Coordonne la planification de voyage (vols, hôtels, activités).',
    instruction="""
    MISSION : Créer un itinéraire complet en appelant les agents nécessaires.
    
    PROCESSUS OBLIGATOIRE (NE SAUTE AUCUNE ÉTAPE) :
    
    1️⃣ Appelle FlightAgent → Récupère la ville de destination
       IMPORTANT : FlightAgent te donnera une liste de vols. GARDE CETTE LISTE.
    
    2️⃣ SI le client demande "activités" ou "restaurants" ou "manger" :
       Appelle ActivityAgent avec la ville trouvée en 1️⃣
       IMPORTANT : ActivityAgent te donnera une liste. GARDE CETTE LISTE.
    
    3️⃣ SI le client parle d'"hôtel" :
       Appelle HotelAgent
    
    ⚠️ RÉPONSE FINALE OBLIGATOIRE (après tous les appels) :
    Tu DOIS afficher TOUTES les listes que tu as reçues, dans cet ordre :
    
    [COPIE ICI EXACTEMENT ce que FlightAgent t'a répondu - garde tous les tirets et détails]
    
    -----------------------------------
    
    [COPIE ICI EXACTEMENT ce que ActivityAgent t'a répondu - garde tous les détails]
    
    INTERDICTION : Ne résume RIEN. Ne transforme RIEN. Copie-colle les réponses brutes.
    """,
    sub_agents=[flight_agent, hotel_agent, activity_agent]
)