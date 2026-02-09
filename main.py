from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import os
import json
import asyncio
from dotenv import load_dotenv

# On charge les variables d'environnement (API Key, etc.)
load_dotenv()

from test_agent.agent import root_agent
import test_agent.agent as agent_module # Nécessaire pour ma petite astuce de sauvegarde ;)
from google.adk.runners import Runner, RunConfig 
from google.adk.sessions import InMemorySessionService
import re

# --- Mes petites classes pour que tout le monde se comprenne ---
class Part:
    def __init__(self, text: str):
        self.text = text

class Message:
    def __init__(self, role: str, parts: list):
        self.role = role
        self.parts = parts
# --------------------------------

# Je stocke les sessions en mémoire pour l'instant
session_service = InMemorySessionService()

app = FastAPI()
# Je configure mes dossiers pour le CSS, les images et les templates HTML
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # La page d'accueil toute belle
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stream_search")
async def stream_search(request: Request, origin: str, destination: str, preferences: str = None):
    print(f"\n📡 NOUVELLE REQUÊTE STREAMING : {origin} -> {destination}")
    
    # Je m'assure que la variable de secours est bien vide avant de commencer
    if hasattr(agent_module, 'last_search_text'):
        agent_module.last_search_text = ""

    async def event_generator():
        # 0. On démarre doucement
        yield f"data: {json.dumps({'type': 'log', 'message': f'🔌 Liaison satellite établie...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # 1. Je prépare le message pour l'agent
        prompt_text = f"Trouve moi un vol de {origin} à {destination}. Préf: {preferences or 'Aucune'}"
        user_msg = Message(role="user", parts=[Part(text=prompt_text)])
        
        yield f"data: {json.dumps({'type': 'log', 'message': f'👤 Client: {prompt_text}'})}\n\n"

        # 2. Config de base (IDs fictifs pour la démo)
        user_id = "user_stream"
        session_id = "session_stream"
        app_name = "travel_agent"

        try:
            await session_service.create_session(
                user_id=user_id, 
                session_id=session_id, 
                app_name=app_name
            )
        except Exception:
            pass # Si la session existe déjà, c'est pas grave, on continue

        yield f"data: {json.dumps({'type': 'log', 'message': f'🧠 Réveil de l\'IA {app_name}...'})}\n\n"

        # 3. Je prépare mon Runner (c'est lui qui fait tout le boulot)
        runner = Runner(
            agent=root_agent, 
            app_name=app_name, 
            session_service=session_service
        )
        
        # L'agent a le droit de réfléchir en plusieurs étapes (outils -> réponse)
        run_config = RunConfig(max_llm_calls=10)
        
        yield f"data: {json.dumps({'type': 'log', 'message': '🤖 L\'agent analyse votre demande...'})}\n\n"

        # C'est parti ! On lance la réflexion
        response_generator = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_msg,
            run_config=run_config
        )

        agent_response = ""
        
        # 4. J'écoute tout ce que l'agent a à dire en temps réel
        try:
            for event in response_generator:
                await asyncio.sleep(0.1) # Petite pause pour l'effet "tape à la machine"
                
                log_msg = ""
                msg_type = "log"
                
                # Cas où l'agent utilise un outil (ex: chercher dans la BDD)
                if hasattr(event, 'function_call'):
                    log_msg = f"🛠️ Outil activé : {event.function_call.name}"
                    msg_type = "tool"
                elif hasattr(event, 'parts'):
                     for part in event.parts:
                        if hasattr(part, 'function_call'):
                             log_msg = f"🛠️ Outil activé : {part.function_call.name}"
                             msg_type = "tool"
                        elif hasattr(part, 'text') and part.text:
                             # Ici, c'est l'agent qui "pense" tout haut
                             log_msg = f"💭 Pensée : {part.text[:50]}..."
                             agent_response += part.text

                # Cas où l'outil répond à l'agent
                if hasattr(event, 'function_response'):
                    log_msg = f"🔙 Retour outil : Données reçues pour {event.function_response.name}"
                
                # Cas où l'agent me répond enfin textuellement
                if hasattr(event, 'text') and event.text:
                    if log_msg == "": 
                        log_msg = f"📝 Réponse : {event.text[:50]}..."
                    agent_response += event.text
                
                # Cas réponse finale et officielle
                if hasattr(event, 'output') and hasattr(event.output, 'text'):
                     log_msg = "🏁 Itinéraire généré avec succès !"
                     agent_response += event.output.text

                # Si j'ai capté un truc intéressant, je l'envoie au front-end
                if log_msg:
                    yield f"data: {json.dumps({'type': msg_type, 'message': log_msg})}\n\n"

        except Exception as e:
            error_msg = str(e)
            if "Resource exhausted" in error_msg or "429" in error_msg:
                 yield f"data: {json.dumps({'type': 'log', 'message': '⚠️ Trafic intense sur l\'IA (Quota dépassé)... Tentative de récupération.'})}\n\n"
            else:
                 yield f"data: {json.dumps({'type': 'error', 'message': f'❌ Oups, petit souci : {error_msg}'})}\n\n"

        # Si jamais l'agent est muet (ou a crashé à cause des quotas), je tente ma technique de secours
        if not agent_response:
             if hasattr(agent_module, 'last_search_text') and agent_module.last_search_text:
                 agent_response = agent_module.last_search_text
                 yield f"data: {json.dumps({'type': 'log', 'message': '⚠️ Plan B activé : Récupération forcée.'})}\n\n"

        # 5. J'extrais les infos importantes (Compagnie, Prix, Heure) pour faire joli
        flights = []
        pattern = r"-\s+(.*?)\s+départ à\s+(.*?)\s+pour\s+(.*?)€"
        matches = re.finditer(pattern, agent_response)
        for match in matches:
            flights.append({
                "airline": match.group(1).strip(),
                "departure": match.group(2).strip(),
                "price": match.group(3).strip()
            })
            
        yield f"data: {json.dumps({'type': 'log', 'message': f'✅ {len(flights)} options trouvées !'})}\n\n"
        
        # Je génère la page de résultats finale
        final_html = templates.get_template("results.html").render({
            "request": request, 
            "response": agent_response,
            "origin": origin,
            "destination": destination,
            "flights": flights
        })
        
        # Et hop, j'envoie tout au navigateur pour l'affichage final
        yield f"data: {json.dumps({'type': 'complete', 'html': final_html})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# La route POST classique (gardée au cas où, mais on utilise le stream maintenant)
@app.post("/search", response_class=HTMLResponse)
async def handle_search(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    preferences: str = Form(None)
):
    print("Cette route ne sert plus qu'en backup !")
    # ... (le reste est identique mais je simplifie pour la lisibilité)
    return await stream_search(request, origin, destination, preferences) # Redirection simple pour éviter le duplicate code si besoin

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)