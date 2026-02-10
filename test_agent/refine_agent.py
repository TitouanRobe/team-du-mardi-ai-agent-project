from google import genai
from google.genai import types
from test_agent.agent import create_agent
from test_agent.activity_agent import search_restaurants, search_activities
from test_agent.hotel_agent import search_hotels
from test_agent.flight_agent import search_flights
import json

# ==========================================
# Agent intelligent de raffinement
# ==========================================

def create_smart_refine_agent(origin: str, destination: str):
    """
    Agent qui analyse la demande utilisateur et décide quels outils appeler.
    Retourne un JSON structuré avec les actions à effectuer.
    """
    
    city = destination or origin
    
    instructions = f"""
Tu es un assistant voyage intelligent qui analyse les demandes de l'utilisateur.

CONTEXTE:
- Trajet: {origin} → {destination or origin}
- Destination principale: {city}

OUTILS DISPONIBLES:
- search_restaurants(city, keyword): Chercher des restaurants (keyword optionnel: "vegan", "tapas", "italien", etc.)
- search_activities(city, keyword): Chercher des activités (keyword optionnel: "musée", "parc", etc.)
- search_hotels(city, budget, amenities): Chercher des hôtels (amenities: "Spa", "Piscine", "WiFi")
- search_flights(origin, destination, max_price): Chercher des vols

TA MISSION:
Analyser la demande de l'utilisateur et retourner un JSON qui indique QUELS outils appeler avec QUELS paramètres.

FORMAT DE RÉPONSE (STRICTEMENT DU JSON, RIEN D'AUTRE):
{{
  "intent": "activities" | "hotels" | "flights" | "mixed",
  "response_message": "Message sympa pour l'utilisateur",
  "actions": [
    {{
      "tool": "search_restaurants" | "search_activities" | "search_hotels" | "search_flights",
      "params": {{
        "city": "{city}",
        "keyword": "tapas" (optionnel),
        "budget": 150 (optionnel),
        "amenities": "Spa" (optionnel),
        "max_price": 500 (optionnel)
      }}
    }}
  ]
}}

EXEMPLES:

User: "je veux un restaurant de tapas"
Assistant: {{
  "intent": "activities",
  "response_message": "Restaurants de tapas à {city}",
  "actions": [
    {{
      "tool": "search_restaurants",
      "params": {{
        "city": "{city}",
        "keyword": "tapas"
      }}
    }}
  ]
}}

User: "trouve-moi des restaurants vegan pas chers"
Assistant: {{
  "intent": "activities",
  "response_message": "Restaurants vegan à {city}",
  "actions": [
    {{
      "tool": "search_restaurants",
      "params": {{
        "city": "{city}",
        "keyword": "vegan"
      }}
    }}
  ]
}}

User: "hôtels avec spa moins de 200€"
Assistant: {{
  "intent": "hotels",
  "response_message": "Hôtels avec spa à moins de 200€",
  "actions": [
    {{
      "tool": "search_hotels",
      "params": {{
        "city": "{city}",
        "budget": 200,
        "amenities": "Spa"
      }}
    }}
  ]
}}

User: "vols moins de 500€"
Assistant: {{
  "intent": "flights",
  "response_message": "Vols à moins de 500€",
  "actions": [
    {{
      "tool": "search_flights",
      "params": {{
        "origin": "{origin}",
        "destination": "{destination or ''}",
        "max_price": 500
      }}
    }}
  ]
}}

User: "des musées et des restaurants italiens"
Assistant: {{
  "intent": "mixed",
  "response_message": "Musées et restaurants italiens",
  "actions": [
    {{
      "tool": "search_activities",
      "params": {{
        "city": "{city}",
        "keyword": "musée"
      }}
    }},
    {{
      "tool": "search_restaurants",
      "params": {{
        "city": "{city}",
        "keyword": "italien"
      }}
    }}
  ]
}}

RÈGLES IMPORTANTES:
1. Retourne UNIQUEMENT du JSON valide, RIEN d'autre (pas de markdown, pas de texte avant/après)
2. Détecte intelligemment les keywords ("tapas", "vegan", "spa", etc.)
3. Extrais les budgets/prix des nombres mentionnés
4. Si l'utilisateur demande plusieurs choses, mets plusieurs actions
5. Le champ "response_message" doit être court et sympa
6. N'invente PAS de paramètres si l'utilisateur ne les a pas mentionnés
"""

    return create_agent(
        name="SmartRefineAgent",
        model="gemini-2.0-flash-exp",
        instruction=instructions,
        tools=[]  # Pas besoin de tools ici, on retourne juste du JSON
    )


async def analyze_user_intent(message: str, origin: str, destination: str, session_service):
    """
    Utilise l'agent Gemini pour analyser l'intent de l'utilisateur.
    Retourne un dict avec les actions à effectuer.
    """
    from google.adk.runners import Runner, RunConfig
    
    agent = create_smart_refine_agent(origin, destination)
    
    user_id = "intent_analyzer"
    session_id = "intent_session"
    app_name = "intent_app"
    
    try:
        await session_service.create_session(user_id=user_id, session_id=session_id, app_name=app_name)
    except:
        pass
    
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    
    from test_agent.flight_agent import Part, Message
    prompt = Message(role="user", parts=[Part(text=message)])
    
    response_text = ""
    
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=prompt,
        run_config=RunConfig(max_llm_calls=1)
    ):
        if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
    
    # Parser le JSON retourné par l'agent
    try:
        # Nettoyer les markdown code blocks si présents
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        intent_data = json.loads(clean_text)
        return intent_data
    except json.JSONDecodeError as e:
        print(f"❌ Erreur parsing JSON de l'agent: {e}")
        print(f"Réponse brute: {response_text}")
        # Fallback: retour simple
        return {
            "intent": "activities",
            "response_message": "Recherche en cours...",
            "actions": [{
                "tool": "search_restaurants",
                "params": {"city": destination or origin}
            }]
        }
