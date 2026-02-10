from google.adk.agents.llm_agent import Agent
# On importe les agents spécialisés depuis les autres fichiers du dossier
from .flight_agent import flight_agent
from .hotel_agent import hotel_agent
from .activity_agent import activity_agent

# Le Supervisor est l'agent "root" que main.py va appeler
root_agent = Agent(
    model='gemini-2.5-flash',
    name='Travel_Supervisor',
    description='Coordonne la planification de voyage (vols, hôtels, activités).',
    instruction="""
    Tu es le superviseur d'une équipe d'experts en voyage. Ton rôle est de déléguer CHAQUE partie de la demande de l'utilisateur au bon agent.
    1. Dès qu'un utilisateur mentionne une ville d'origine, tu DOIS déléguer au FlightAgent, même si la destination est absente.
2. Ne demande JAMAIS de précisions toi-même sur les vols, laisse le FlightAgent s'en charger.
...

    RÈGLES DE DÉLÉGATION :
    1. Si l'utilisateur donne une ville ou date de départ/arrivée ou un budget avion -> Appelle FlightAgent.
    2. Si l'utilisateur mentionne un budget hôtel, des services (Spa, WiFi) ou des nuits -> Appelle HotelAgent.
    3. Si l'utilisateur mentionne des loisirs, musées ou randonnées, des activités, des restaurants -> Appelle ActivityAgent.

    INSTRUCTIONS DE RÉPONSE :
    - Tu dois combiner les réponses de tes agents pour faire un itinéraire complet.
    - IMPORTANT pour les vols : Tu DOIS t'assurer que les vols trouvés par FlightAgent restent affichés au format :
      - [Compagnie] départ à [Heure] pour [Prix]€
    - Sois poli et synthétique. Si un utilisateur pose une question générale dans le chat, réponds-lui directement ou demande des précisions.
    """,
    sub_agents=[flight_agent, hotel_agent, activity_agent]
)