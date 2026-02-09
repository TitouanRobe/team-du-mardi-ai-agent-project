from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv

# Charge le fichier .env immédiatement
load_dotenv()

from test_agent.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# --- FIX DÉFINITIF : On crée les classes nous-mêmes ---
# On n'importe RIEN de google.adk.types pour éviter l'erreur ModuleNotFoundError
class Part:
    def __init__(self, text: str):
        self.text = text

class Message:
    def __init__(self, role: str, parts: list):
        self.role = role
        self.parts = parts
# -------------------------------------------------------

# 1. Service de session global
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
    prompt_text = f"Trouve moi un vol de {origin} à {destination}. Préf: {preferences or 'Aucune'}"
    
    user_msg = Message(
        role="user",
        parts=[Part(text=prompt_text)]
    )

    user_id = "user_123"
    session_id = "session_123"
    app_name = "travel_agent"

    try:
        await session_service.create_session(
            user_id=user_id, 
            session_id=session_id, 
            app_name=app_name
        )
    except Exception:
        pass

    runner = Runner(
        agent=root_agent, 
        app_name=app_name, 
        session_service=session_service
    )
    
    response_generator = runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=user_msg
    )
    
    agent_response = ""
    try:
        for event in response_generator:
            if hasattr(event, 'text') and event.text:
                agent_response += event.text
            elif hasattr(event, 'parts') and event.parts:
                 agent_response += event.parts[0].text
    except Exception as e:
        print(f"Erreur pendant la lecture de réponse: {e}")
            
    if not agent_response:
        agent_response = "L'agent a bien reçu la demande mais n'a pas renvoyé de texte (Vérifiez les logs console)."

    return templates.TemplateResponse("results.html", {
        "request": request, 
        "response": agent_response,
        "origin": origin,
        "destination": destination
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)