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

from test_agent.supervisor import root_agent
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
async def stream_search(
    request: Request, 
    origin: str, 
    destination: str, 
    preferences: str = None,
    budget_max: str = None, 
    airline: str = None,
    date: str = None
    ):
    print(f"\n📡 NOUVELLE REQUÊTE STREAMING : {origin} -> {destination}")
    
    # Je m'assure que la variable de secours est bien vide avant de commencer


    async def event_generator():
        yield f"data: {json.dumps({'type': 'log', 'message': f'🔌 Liaison satellite établie...'})}\n\n"
        await asyncio.sleep(0.5)
        
        prompt_text = f"Je pars de {origin}."
        if destination: prompt_text += f" Ma destination est {destination}."
        if date: prompt_text += f" Je souhaite partir le {date}."
        if budget_max: prompt_text += f" Budget max avion : {budget_max}€."
        if airline: prompt_text += f" Je préfère voyager avec {airline}."
        if preferences: prompt_text += f" Notes : {preferences}."

        user_msg = Message(role="user", parts=[Part(text=prompt_text)])
        
        yield f"data: {json.dumps({'type': 'log', 'message': f'👤 Client: {prompt_text}'})}\n\n"

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

        yield f"data: {json.dumps({'type': 'log', 'message': f'Réveil de l\'IA {app_name}...'})}\n\n"

        runner = Runner(
            agent=root_agent, 
            app_name=app_name, 
            session_service=session_service
        )
        
        run_config = RunConfig(max_llm_calls=10)
        
        yield f"data: {json.dumps({'type': 'log', 'message': '🤖 L\'agent analyse votre demande...'})}\n\n"
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
                await asyncio.sleep(0.1) 
                
                log_msg = ""
                msg_type = "log"
                
                # On regarde si l'événement contient du contenu (Event standard)
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        
                        # 1. Cas d'appel de fonction (l'agent veut chercher un vol)
                        if hasattr(part, 'function_call') and part.function_call:
                             log_msg = f"🛠️ Outil activé : {part.function_call.name}"
                             msg_type = "tool"
                        
                        # 2. Cas de réponse de fonction (l'outil a répondu)
                        elif hasattr(part, 'function_response') and part.function_response:
                             log_msg = f"🔙 Retour outil : Données reçues pour {part.function_response.name}"

                        # 3. Cas de texte (l'agent parle)
                        elif hasattr(part, 'text') and part.text:
                             # Ici, c'est l'agent qui "pense" tout haut ou répond
                             log_msg = f"📝 Réponse : {part.text[:50]}..."
                             agent_response += part.text

                if log_msg:
                    yield f"data: {json.dumps({'type': msg_type, 'message': log_msg})}\n\n"

        except Exception as e:
            print(f"DEBUG EXCEPTION: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'erreur : {str(e)}'})}\n\n"

        # --- DEBUG MODE ---
        print(f"\n📝 RÉPONSE BRUTE DE L'AGENT :\n{agent_response}")
        print(f"-----------------------------------\n")
        flights = []
        # On rend le tiret '-' optionnel (\-?) et on est plus souple sur les espaces
        pattern = r"\-?\s*(.*?)\s+\((.*?)\)\s*:\s*(.*?)\s*->\s*(.*?)\s*\|\s*départ\s+(.*?)\s+arrivée\s+(.*?)\s+pour\s+(.*?)€"
        
        matches = re.finditer(pattern, agent_response)
        for match in matches:
            flights.append({
                "airline": f"{match.group(1)} ({match.group(2)})",
                "origin": match.group(3).strip(),
                "destination": match.group(4).strip(),
                "departure": match.group(5).strip(),
                "arrival": match.group(6).strip(),
                "price": match.group(7).strip()
            })
            
        yield f"data: {json.dumps({'type': 'log', 'message': f'✅ {len(flights)} options trouvées !'})}\n\n"
        
        final_html = templates.get_template("results.html").render({
            "request": request, 
            "response": agent_response,
            "origin": origin,
            "destination": destination,
            "flights": flights
        })
        
        yield f"data: {json.dumps({'type': 'complete', 'html': final_html})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/search", response_class=HTMLResponse)
async def handle_search(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    preferences: str = Form(None)
):
    print("Cette route ne sert plus qu'en backup !")
    return await stream_search(request, origin, destination, preferences) 

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)