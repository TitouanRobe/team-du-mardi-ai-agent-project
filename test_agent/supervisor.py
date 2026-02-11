from google.adk.agents.llm_agent import Agent

# Import tools
from .flight_agent import search_flights
from .hotel_agent import search_hotels
from .activity_agent import search_activities, search_restaurants

# Import sub-agents for root_agent
from .flight_agent import flight_agent
from .hotel_agent import hotel_agent
from .activity_agent import activity_agent


# ═══════════════════════════════════════════════════════
# AGENT 1 : root_agent (recherche initiale)
# Utilise les tools DIRECTEMENT pour appeler les 4 en parallèle
# ═══════════════════════════════════════════════════════

root_agent = Agent(
    model='gemini-2.5-flash',
    name='Travel_Supervisor',
    description='Coordonne la planification de voyage complète.',
    instruction="""
    Tu es le SUPERVISOR de TravelAgent.ai.
    
    ⚠️ RÈGLE NUMÉRO 1 : Tu ne poses JAMAIS de questions. Tu agis IMMÉDIATEMENT.
    
    ═══ COMMENT DÉCIDER QUOI APPELER ═══
    
    Analyse le message et appelle UNIQUEMENT les outils pertinents :
    
    - TRAJET mentionné → search_flights(origin, destination, ...)
    - ACTIVITÉS mentionnées → search_activities(city, keyword)
    - RESTAURANTS mentionnés → search_restaurants(city, keyword)
    - HÔTEL mentionné → search_hotels(city, budget, amenities)
    - DEMANDE COMPLÈTE de voyage → les 4 outils
    
    ═══ FORMAT DE RÉPONSE ═══
    
    Copie le TEXTE BRUT de chaque outil dans les balises correspondantes :
    
    ### DEBUT_VOLS ###
    - United (LH724) : Berlin -> Madrid | départ 2026-04-20 15:37 arrivée 2026-04-21 01:37 pour 667.0€
    ### FIN_VOLS ###
    ### DEBUT_ACTIVITES ###
    Activité, Musée du Prado, 15.0€, Entrée musée d'art.
    Restaurant, Vega, 25.0€, Tapas et plats espagnols Vegan.
    ### FIN_ACTIVITES ###
    ### DEBUT_HOTELS ###
    - Madrid Budget Inn 38 à Madrid pour 90.0€/nuit (Dispo: 2026-03-22 au 2026-04-06, Services: Piscine)
    ### FIN_HOTELS ###
    
    ═══ RÈGLES ═══
    - INTERDICTION de JSON, de blocs ```code```, ou de markdown
    - Copie le texte brut des outils ligne par ligne
    - N'inclus QUE les sections pour lesquelles tu as appelé un outil
    - Ne pose AUCUNE question
    """,
    tools=[search_flights, search_hotels, search_activities, search_restaurants],
    sub_agents=[flight_agent, hotel_agent, activity_agent]
)


# ═══════════════════════════════════════════════════════
# AGENT 2 : refine_supervisor (chat de raffinement)
# Utilise transfer_to_agent pour ROUTER vers le bon sub-agent
# On crée des INSTANCES SÉPARÉES car ADK interdit qu'un agent
# ait deux parents.
# ═══════════════════════════════════════════════════════

# Copies dédiées des sub-agents pour le refine_supervisor
refine_flight_agent = Agent(
    name="RefineFlightAgent",
    model="gemini-2.5-flash",
    description="Expert en recherche de vols. Utilise l'outil search_flights pour trouver des vols selon origin, destination, date, budget et compagnie.",
    instruction="""
    Tu es un agent de recherche de vols.
    
    Dès que tu reçois une demande, appelle search_flights immédiatement.
    Extrais origin et destination du message. Si un budget, une date ou une compagnie
    sont mentionnés, passe-les aussi.
    
    Retourne le résultat de l'outil EXACTEMENT tel quel. Ne pose jamais de questions.
    """,
    tools=[search_flights]
)

refine_hotel_agent = Agent(
    model='gemini-2.5-flash',
    name='refine_hotel_agent',
    description="Expert en recherche d'hôtels. Utilise l'outil search_hotels pour trouver des hôtels selon la ville, le budget et les services.",
    instruction="""
    Tu es un agent de recherche d'hôtels.
    
    Dès que tu reçois une demande, appelle search_hotels immédiatement.
    Extrais la ville de destination. Si un budget ou des services sont mentionnés, passe-les aussi.
    
    Retourne le résultat de l'outil EXACTEMENT tel quel. Ne pose jamais de questions.
    """,
    tools=[search_hotels]
)

refine_activity_agent = Agent(
    model='gemini-2.5-flash',
    name='refine_activity_agent',
    description="Guide touristique expert. Utilise search_activities et search_restaurants pour trouver des activités et restaurants.",
    instruction="""
    Tu es un MOTEUR DE RECHERCHE ET DE FILTRAGE SÉMANTIQUE.
    
    TA MISSION :
    1. APPEL DES OUTILS : Appelle `search_restaurants` ou `search_activities` en utilisant la VILLE. 
       (Privilégie des recherches larges pour récupérer le maximum de choix bruts).
       
    2. FILTRAGE SÉMANTIQUE (CRITIQUE) : 
       Tu vas recevoir une liste brute. Tu NE DOIS PAS la renvoyer telle quelle.
       Utilise ton intelligence pour analyser la description de CHAQUE lieu.
       - Le lieu correspond-il à l'ESPRIT de la demande de l'utilisateur ?
       - Exemple : Si on demande "street-food", garde les "food-trucks", les "stands", les lieux "sur le pouce", même si le mot "street-food" n'est pas écrit textuellement.
       - Exemple : Si on demande "romantique", cherche les descriptions parlant de "bougies", "intimiste", "belle vue", etc.
       - JETTE impitoyablement tout ce qui est hors sujet.
       
    3. FORMAT DE SORTIE :
       Affiche UNIQUEMENT les résultats qui ont passé ton filtre intelligent.
       Garde la structure technique de base par ligne : `Type, Nom, Prix, Description`.
    """,
    tools=[search_activities, search_restaurants]
)

refine_supervisor = Agent(
    model='gemini-2.5-flash',
    name='Refine_Supervisor',
    description='Route les demandes de raffinement vers le bon agent spécialisé.',
    instruction="""
    Tu es le ROUTEUR de TravelAgent.ai pour les demandes de raffinement.
    
    L'utilisateur a déjà ses résultats de voyage. Il veut AFFINER sa recherche.
    Tu dois analyser sa demande et la TRANSFÉRER au bon agent spécialisé.
    
    ═══ RÈGLES DE ROUTAGE ═══
    
    Si la demande concerne des RESTAURANTS, de la NOURRITURE, manger, cuisine, tapas, vegan, gastronomie :
    → Transfère à refine_activity_agent
    
    Si la demande concerne des ACTIVITÉS, musées, visites, tourisme, parcs, monuments :
    → Transfère à refine_activity_agent
    
    Si la demande concerne des HÔTELS, hébergement, logement, spa, piscine, budget hôtel :
    → Transfère à refine_hotel_agent
    
    Si la demande concerne des VOLS, avions, compagnies aériennes, budget vol, dates de vol :
    → Transfère à RefineFlightAgent
    
    ═══ COMPORTEMENT ═══
    - Tu TRANSFÈRES immédiatement, sans poser de questions
    - Tu ne réponds JAMAIS toi-même, tu délègues TOUJOURS
    - UN SEUL transfert par demande
    """,
    sub_agents=[refine_flight_agent, refine_hotel_agent, refine_activity_agent]
)