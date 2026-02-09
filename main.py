from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv

# Charge le fichier .env
load_dotenv()

from test_agent.agent import root_agent
import test_agent.agent as agent_module # Import du module pour le hack (Sauvegarde)
from google.adk.runners import Runner, RunConfig 
from google.adk.sessions import InMemorySessionService

# --- Classes de compatibilité ---
class Part:
    def __init__(self, text: str):
        self.text = text

class Message:
    def __init__(self, role: str, parts: list):
        self.role = role
        self.parts = parts
# --------------------------------

# Service de session
session_service = InMemorySessionService()

app = FastAPI()
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def handle_search(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    preferences: str = Form(None)
):
    print(f"\n📨 NOUVELLE REQUÊTE : {origin} -> {destination}")
    
    # Reset du hack
    if hasattr(agent_module, 'last_search_text'):
        agent_module.last_search_text = ""

    # 1. Message
    prompt_text = f"Trouve moi un vol de {origin} à {destination}. Préf: {preferences or 'Aucune'}"
    user_msg = Message(role="user", parts=[Part(text=prompt_text)])

    # 2. Paramètres
    user_id = "user_123"
    session_id = "session_123"
    app_name = "travel_agent"

    # 3. Session (Création brute)
    try:
        await session_service.create_session(
            user_id=user_id, 
            session_id=session_id, 
            app_name=app_name
        )
    except Exception:
        pass 

    # 4. Runner
    runner = Runner(
        agent=root_agent, 
        app_name=app_name, 
        session_service=session_service
    )
    
    # Configuration pour autoriser plusieurs tours (Function Call -> Tool Output -> Response)
    run_config = RunConfig(max_llm_calls=10)

    response_generator = runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=user_msg,
        run_config=run_config
    )
    
    # 5. Boucle de lecture "Tout Terrain"
    agent_response = ""
    print("⏳ Lecture du flux de réponse...")
    
    try:
        for event in response_generator:
            # DEBUG : On affiche ce qu'on reçoit pour comprendre
            # print(f"   -> Event reçu: {type(event)}")

            # Cas 1 : Texte direct
            if hasattr(event, 'text') and event.text:
                print(f"   📝 Texte reçu : {event.text}")
                agent_response += event.text
            
            # Cas 2 : Parties multiples (souvent là que ça se cache)
            elif hasattr(event, 'parts'):
                for part in event.parts:
                    # On vérifie si c'est du texte
                    if hasattr(part, 'text') and part.text:
                        print(f"   📝 Texte (via parts) : {part.text}")
                        agent_response += part.text
                    elif hasattr(part, 'function_call'):
                        print(f"   ⚙️ Appel de fonction : {part.function_call.name}")

            # Cas 3 : Candidats (Structure Gemini parfois)
            elif hasattr(event, 'candidates'):
                for cand in event.candidates:
                    if hasattr(cand, 'content') and hasattr(cand.content, 'parts'):
                        for part in cand.content.parts:
                            if hasattr(part, 'text') and part.text:
                                print(f"   📝 Texte (via candidates) : {part.text}")
                                agent_response += part.text
            
            # Cas 4 : Si c'est un objet "Turn" ou résultat d'étape finale
            if hasattr(event, 'output') and hasattr(event.output, 'text'):
                 print(f"   📝 Texte (via output) : {event.output.text}")
                 agent_response += event.output.text

    except Exception as e:
        print(f"❌ Erreur dans la boucle : {e}")
            
    # Fallback ULTIME via le hack
    if not agent_response:
        print("⚠️ Réponse vide du Runner.")
        # On vérifie si l'agent a stocké le résultat dans la variable globale (via le hack)
        if hasattr(agent_module, 'last_search_text') and agent_module.last_search_text:
             print("✅ Sauvetage via variable globale !")
             agent_response = agent_module.last_search_text
        else:
             print("❌ Échec total.")
             agent_response = "J'ai trouvé les vols (voir terminal), mais l'affichage du texte final a échoué."

    # 6. Parsing de la réponse pour l'affichage "Classe"
    import re
    flights = []
    # Pattern pour capturer : Compagnie, Date/Heure, Prix
    # Exemple : "- United départ à 2026-04-17 02:00 pour 1131.0€"
    pattern = r"-\s+(.*?)\s+départ à\s+(.*?)\s+pour\s+(.*?)€"
    
    matches = re.finditer(pattern, agent_response)
    for match in matches:
        flights.append({
            "airline": match.group(1).strip(),
            "departure": match.group(2).strip(),
            "price": match.group(3).strip()
        })

    return templates.TemplateResponse("results.html", {
        "request": request, 
        "response": agent_response,
        "origin": origin,
        "destination": destination,
        "flights": flights # On passe la liste structurée
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)