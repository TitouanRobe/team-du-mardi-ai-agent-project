from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import os
import json
import asyncio
import re
from dotenv import load_dotenv

load_dotenv()

# Import des 3 agents directement (plus de superviseur!)
from test_agent.flight_agent import flight_agent
from test_agent.activity_agent import activity_agent
from test_agent.hotel_agent import hotel_agent
from google.adk.runners import Runner, RunConfig 
from google.adk.sessions import InMemorySessionService  

class Part:
    def __init__(self, text: str):
        self.text = text

class Message:
    def __init__(self, role: str, parts: list):
        self.role = role
        self.parts = parts

session_service = InMemorySessionService()

app = FastAPI()
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stream_search")
async def stream_search(
    request: Request, 
    origin: str, 
    destination: str, 
    preferences: str = None,
    budget_max: str = None, 
    airline: str = None,
    date: str = None,
    activities: str = None,
    hotel_budget_max: str = None,
    amenities: str = None
    ):
    
    print(f"\n📡 NOUVELLE REQUÊTE : {origin} -> {destination} | Activités: {activities} | Hôtels: {amenities}")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'log', 'message': f'🔌 Connexion...'})}\n\n"
        await asyncio.sleep(0.5)
        
        target = destination if destination else origin
        
        # --- CONFIGURATION SESSION ---
        user_id = "user_stream"
        session_id = "session_stream"
        app_name = "travel_agent"

        # Créer les 3 sessions dont on aura besoin
        try: 
            await session_service.create_session(user_id=user_id, session_id=f"{session_id}_flight", app_name=app_name)
            await session_service.create_session(user_id=user_id, session_id=f"{session_id}_activity", app_name=app_name)
            await session_service.create_session(user_id=user_id, session_id=f"{session_id}_hotel", app_name=app_name)
        except: pass

        # --- APPEL SÉQUENTIEL DES 3 AGENTS (on stocke immédiatement chaque résultat) ---
        
        flights_text = ""
        activities_text = ""
        hotels_text = ""
        
        run_config = RunConfig(max_llm_calls=10)
        
        # 1. FLIGHT AGENT
        yield f"data: {json.dumps({'type': 'tool', 'message': '✈️ Recherche de vols...'})}\n\n"
        flight_runner = Runner(agent=flight_agent, app_name=app_name, session_service=session_service)
        
        # Prompt explicite pour que l'agent utilise bien tous les paramètres
        flight_prompt_text = f"Appelle l'outil search_flights avec ces paramètres EXACTS :\n"
        flight_prompt_text += f"- origin: '{origin}'\n"
        flight_prompt_text += f"- destination: '{destination or ''}'\n"
        if budget_max:
            flight_prompt_text += f"- max_price: {budget_max}\n"
        if airline:
            flight_prompt_text += f"- preferred_airline: '{airline}'\n"
        if date:
            flight_prompt_text += f"- preferred_date: '{date}'\n"
        
        flight_prompt = Message(role="user", parts=[Part(text=flight_prompt_text)])

        
        try:
            for event in flight_runner.run(user_id=user_id, session_id=f"{session_id}_flight", new_message=flight_prompt, run_config=run_config):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            flights_text += part.text
        except Exception as e:
            flights_text = f"Erreur vols: {e}"
            
        print(f"📝 VOLS:\n{flights_text}\n---")
        
        # 2. ACTIVITY AGENT
        yield f"data: {json.dumps({'type': 'tool', 'message': '🎭 Recherche activités...'})}\n\n"
        activity_runner = Runner(agent=activity_agent, app_name=app_name, session_service=session_service)
        
        # Décider quel type d'activité chercher selon le formulaire
        if activities and "restaurant" in activities.lower():
            activity_prompt_text = f"Appelle UNIQUEMENT l'outil search_restaurants avec city='{target}'"
        elif activities and activities.lower() not in ["", "tous", "toutes"]:
            activity_prompt_text = f"Appelle UNIQUEMENT l'outil search_activities avec city='{target}'"
        else:
            # Si vide ou "tous", chercher les deux
            activity_prompt_text = f"Appelle les DEUX outils : search_restaurants(city='{target}') ET search_activities(city='{target}')"
        
        activity_prompt = Message(role="user", parts=[Part(text=activity_prompt_text)])

        
        try:
            for event in activity_runner.run(user_id=user_id, session_id=f"{session_id}_activity", new_message=activity_prompt, run_config=run_config):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            activities_text += part.text
        except Exception as e:
            activities_text = f"Erreur activités: {e}"
            
        print(f"📝 ACTIVITÉS:\n{activities_text}\n---")
        
        # 3. HOTEL AGENT
        yield f"data: {json.dumps({'type': 'tool', 'message': '🏨 Recherche hôtels...'})}\n\n"
        hotel_runner = Runner(agent=hotel_agent, app_name=app_name, session_service=session_service)
        
        # Prompt explicite pour les paramètres
        hotel_prompt_text = f"Appelle l'outil search_hotels avec ces paramètres EXACTS :\n"
        hotel_prompt_text += f"- city: '{target}'\n"
        if hotel_budget_max:
            hotel_prompt_text += f"- budget: {hotel_budget_max}\n"
        if amenities:
            hotel_prompt_text += f"- amenities: '{amenities}'\n"
        
        hotel_prompt = Message(role="user", parts=[Part(text=hotel_prompt_text)])

        
        try:
            for event in hotel_runner.run(user_id=user_id, session_id=f"{session_id}_hotel", new_message=hotel_prompt, run_config=run_config):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            hotels_text += part.text
        except Exception as e:
            hotels_text = f"Erreur hôtels: {e}"
            
        print(f"📝 HÔTELS:\n{hotels_text}\n---")

        # --- PARSING (sur les 3 textes séparés) ---
        
        flights = []
        act_list = []
        hotels_list = []
        
        # 1. PARSING VOLS
        flight_pattern = r"-\s+([^(]+)\s+\(([^)]+)\)\s+:\s+(.*?)\s+->\s+(.*?)\s+\|\s+départ\s+(.*?)\s+arrivée\s+(.*?)\s+pour\s+([\d.]+)€"
        for m in re.finditer(flight_pattern, flights_text):
            flights.append({
                "airline": f"{m.group(1)} ({m.group(2)})",
                "departure": m.group(5).strip(),
                "price": m.group(7).strip()
            })

        # 2. PARSING ACTIVITÉS
        act_pattern = r"(Activité|Restaurant),\s*([^,]+),\s*([\d.]+)€,\s*(.*)"
        for m in re.finditer(act_pattern, activities_text):
            act_list.append({
                "type": m.group(1),
                "name": m.group(2),
                "price": m.group(3),
                "description": m.group(4)
            })

        # 3. PARSING HÔTELS
        hotel_pattern = r"-\s+([^à]+)\s+à\s+([^p]+)\s+pour\s+([\d.]+)€/nuit\s+\(Dispo:\s+([^a]+)\s+au\s+([^,]+),\s+Services:\s+(.*)\)"
        for m in re.finditer(hotel_pattern, hotels_text):
            serv = m.group(6).strip()
            if serv.endswith(")"): serv = serv[:-1]
            hotels_list.append({
                "name": m.group(1),
                "price": m.group(3),
                "amenities": serv
            })

        yield f"data: {json.dumps({'type': 'log', 'message': f'✅ Résultats : {len(flights)} Vols, {len(act_list)} Activités, {len(hotels_list)} Hôtels'})}\n\n"
        print(f"📊 STATS : {len(flights)} Vols | {len(act_list)} Activités | {len(hotels_list)} Hôtels")

        final_html = templates.get_template("results.html").render({
            "request": request, 
            "response": f"Vols:\n{flights_text}\n\nActivités:\n{activities_text}\n\nHôtels:\n{hotels_text}",
            "flights": flights,
            "activities": act_list,
            "hotels": hotels_list
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