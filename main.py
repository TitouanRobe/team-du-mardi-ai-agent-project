from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import os
import json
import asyncio
from dotenv import load_dotenv

# Charge le fichier .env
load_dotenv()

from test_agent.agent import root_agent
import test_agent.agent as agent_module # Import du module pour le hack (Sauvegarde)
from google.adk.runners import Runner, RunConfig 
from google.adk.sessions import InMemorySessionService
import re

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

@app.get("/stream_search")
async def stream_search(request: Request, origin: str, destination: str, preferences: str = None):
    print(f"\n📡 NOUVELLE REQUÊTE STREAMING : {origin} -> {destination}")
    
    # Reset du hack
    if hasattr(agent_module, 'last_search_text'):
        agent_module.last_search_text = ""

    async def event_generator():
        # 0. Initialisation
        yield f"data: {json.dumps({'type': 'log', 'message': f'🔌 Connexion au serveur établie...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # 1. Message
        prompt_text = f"Trouve moi un vol de {origin} à {destination}. Préf: {preferences or 'Aucune'}"
        user_msg = Message(role="user", parts=[Part(text=prompt_text)])
        
        yield f"data: {json.dumps({'type': 'log', 'message': f'👤 User: {prompt_text}'})}\n\n"

        # 2. Setup Session (Mock ID for demo)
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
            pass 

        yield f"data: {json.dumps({'type': 'log', 'message': f'🧠 Initialisation de l\'agent {app_name}...'})}\n\n"

        # 3. Runner
        runner = Runner(
            agent=root_agent, 
            app_name=app_name, 
            session_service=session_service
        )
        
        run_config = RunConfig(max_llm_calls=10)
        
        # Lancement (Note: runner.run est synchrone dans cette version de l'ADK, mais on va essayer de capturer les étapes si possible)
        # S'il est 100% bloquant, on aura les logs "en bloc" à la fin, sauf si l'ADK stream lui-même.
        # Pour une démo parfaite, on va simuler un peu de "streaming" avant l'appel réel ou espérer que le générateur soit itératif.
        
        yield f"data: {json.dumps({'type': 'log', 'message': '🤖 L\'agent réfléchit...'})}\n\n"

        # On appelle le runner
        response_generator = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_msg,
            run_config=run_config
        )

        agent_response = ""
        
        # 4. Lecture de la boucle
        try:
            for event in response_generator:
                await asyncio.sleep(0.1) # Petit délai pour l'effet visuel streaming
                
                # Analyse de l'événement pour les logs
                log_msg = ""
                msg_type = "log"
                
                # Cas Function Call (Outil)
                if hasattr(event, 'function_call'):
                    log_msg = f"🛠️ CALL TOOL: {event.function_call.name}"
                    msg_type = "tool"
                elif hasattr(event, 'parts'):
                     for part in event.parts:
                        if hasattr(part, 'function_call'):
                             log_msg = f"🛠️ CALL TOOL: {part.function_call.name}"
                             msg_type = "tool"
                        elif hasattr(part, 'text') and part.text:
                             # C'est du texte de pensée ou de réponse
                             log_msg = f"💭 {part.text[:50]}..."
                             agent_response += part.text

                # Cas retour d'outil (Function Response)
                if hasattr(event, 'function_response'):
                    log_msg = f"🔙 TOOL RETURN: {event.function_response.name}"
                
                # Cas réponse finale textuelle
                if hasattr(event, 'text') and event.text:
                    if log_msg == "": # Si pas déjà loggé
                        log_msg = f"📝 {event.text[:50]}..."
                    agent_response += event.text
                
                # Cas "output" final
                if hasattr(event, 'output') and hasattr(event.output, 'text'):
                     log_msg = "🏁 Réponse finale générée"
                     agent_response += event.output.text

                if log_msg:
                    yield f"data: {json.dumps({'type': msg_type, 'message': log_msg})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'❌ Erreur: {str(e)}'})}\n\n"

        # Fallback si vide
        if not agent_response:
             if hasattr(agent_module, 'last_search_text') and agent_module.last_search_text:
                 agent_response = agent_module.last_search_text
                 yield f"data: {json.dumps({'type': 'log', 'message': '⚠️ Récupération via variable globale.'})}\n\n"

        # 5. Parsing & Construction du HTML final
        flights = []
        pattern = r"-\s+(.*?)\s+départ à\s+(.*?)\s+pour\s+(.*?)€"
        matches = re.finditer(pattern, agent_response)
        for match in matches:
            flights.append({
                "airline": match.group(1).strip(),
                "departure": match.group(2).strip(),
                "price": match.group(3).strip()
            })
            
        yield f"data: {json.dumps({'type': 'log', 'message': f'✅ {len(flights)} vols trouvés.'})}\n\n"
        
        # Rendu du template results.html en string
        # Astuce : On rend le template complet et le client remplacera tout le body
        final_html = templates.get_template("results.html").render({
            "request": request, 
            "response": agent_response,
            "origin": origin,
            "destination": destination,
            "flights": flights
        })
        
        # Envoi de l'événement "complete" avec le HTML
        # On encode le HTML en JSON pour éviter les problèmes de saut de ligne dans SSE
        yield f"data: {json.dumps({'type': 'complete', 'html': final_html})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ... (Keep existing handle_search for backward compatibility if needed, or replace it)
# We keep handle_search but the frontend will use stream_search now.

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