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
        activities_text = ""
        
        # Si le champ activités est vide, on n'appelle PAS l'agent (onglet vide)
        if activities and activities.strip():
            yield f"data: {json.dumps({'type': 'tool', 'message': '🎭 Recherche activités...'})}\n\n"
            activity_runner = Runner(agent=activity_agent, app_name=app_name, session_service=session_service)
            
            # Décider quel type d'activité chercher selon le formulaire
            if "restaurant" in activities.lower():
                activity_prompt_text = f"Appelle UNIQUEMENT l'outil search_restaurants avec city='{target}'"
            else:
                activity_prompt_text = f"Appelle UNIQUEMENT l'outil search_activities avec city='{target}'"
            
            activity_prompt = Message(role="user", parts=[Part(text=activity_prompt_text)])

            
            try:
                for event in activity_runner.run(user_id=user_id, session_id=f"{session_id}_activity", new_message=activity_prompt, run_config=run_config):
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                activities_text += part.text
            except Exception as e:
                activities_text = f"Erreur activités: {e}"
        else:
            # Champ vide → Pas de recherche
            yield f"data: {json.dumps({'type': 'log', 'message': '⏭️ Activités non demandées'})}\n\n"

            
        print(f"📝 ACTIVITÉS:\n{activities_text}\n---")
        
        # 3. HOTEL AGENT
        hotels_text = ""
        
        # Si pas de filtre hôtel demandé, on peut aussi ne rien chercher
        # (À vous de décider si vous voulez toujours chercher les hôtels ou non)
        if amenities and amenities.strip():
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
        else:
            # Pas de critère spécifique → Pas de recherche
            yield f"data: {json.dumps({'type': 'log', 'message': '⏭️ Hôtels non demandés'})}\n\n"

            
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
    

# REMPLACER LES LIGNES 240-444 dans main.py par ce code:

@app.get("/chat_refine")
async def chat_refine(request: Request, message: str, origin: str, destination: str):
    print(f"\n💬 CHAT REFINE: {message}")
    
    async def event_generator():
        target = destination if destination else origin
        message_lower = message.lower()
        
        # Détection d'intent
        call_activities = any(word in message_lower for word in ['restaurant', 'vegan', 'végétarien', 'végé', 'activité', 'musée'])
        call_hotels = any(word in message_lower for word in ['hôtel', 'hotel', 'spa', 'piscine', 'wifi'])
        call_flights = any(word in message_lower for word in ['vol', 'avion'])
        
        flights_data, activities_data, hotels_data = [], [], []
        run_config = RunConfig()
        user_id, session_id_base, app_name = "chat_user", "chat_session", "travel_chat"
        
        try:
            await session_service.create_session(user_id=user_id, session_id=f"{session_id_base}_flight", app_name=app_name)
            await session_service.create_session(user_id=user_id, session_id=f"{session_id_base}_activity", app_name=app_name)
            await session_service.create_session(user_id=user_id, session_id=f"{session_id_base}_hotel", app_name=app_name)
        except: pass
        
        response_message = "Voici les résultats affinés"
        
        # ACTIVITIES
        if call_activities:
            yield f"data: {json.dumps({'type': 'log', 'message': '🍴 Recherche...'})}\\n\\n"
            activity_runner = Runner(agent=activity_agent, app_name=app_name, session_service=session_service)
            
            if "vegan" in message_lower or "végé" in message_lower:
                activity_prompt_text = f"Appelle UNIQUEMENT search_restaurants avec city='{target}'"
                response_message = "Restaurants vegan/végétariens uniquement"
            elif "restaurant" in message_lower:
                activity_prompt_text = f"Appelle UNIQUEMENT search_restaurants avec city='{target}'"
            else:
                activity_prompt_text = f"Appelle UNIQUEMENT search_activities avec city='{target}'"
            
            activity_prompt = Message(role="user", parts=[Part(text=activity_prompt_text)])
            activities_text = ""
            try:
                for event in activity_runner.run(user_id=user_id, session_id=f"{session_id_base}_activity", new_message=activity_prompt, run_config=run_config):
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                activities_text += part.text
            except Exception as e:
                print(f"Erreur activity: {e}")
            
            # Parser avec regex corrigé (SIMPLE BACKSLASH)
            act_pattern = r"(Restaurant|Activité), ([^,]+), ([\d.]+)€, (.+)"
            for m in re.finditer(act_pattern, activities_text):
                desc = m.group(4).strip()
                if "vegan" in message_lower or "végé" in message_lower:
                    if "vegan" in desc.lower() or "végé" in desc.lower():
                        activities_data.append({"type": m.group(1).strip(), "name": m.group(2).strip(), "price": float(m.group(3)), "description": desc})
                else:
                    activities_data.append({"type": m.group(1).strip(), "name": m.group(2).strip(), "price": float(m.group(3)), "description": desc})
        
        # HOTELS
        if call_hotels:
            yield f"data: {json.dumps({'type': 'log', 'message': '🏨 Recherche hôtels...'})}\\n\\n"
            hotel_runner = Runner(agent=hotel_agent, app_name=app_name, session_service=session_service)
            
            budget_match = re.search(r'(\d+)\s*€', message)
            budget_filter = int(budget_match.group(1)) if budget_match else None
            
            amenities_filter = None
            if "spa" in message_lower:
                amenities_filter = "Spa"
                response_message = "Hôtels avec Spa"
            elif "piscine" in message_lower:
                amenities_filter = "Piscine"
                response_message = "Hôtels avec Piscine"
            
            hotel_prompt_text = f"Appelle search_hotels avec city='{target}'"
            if budget_filter:
                hotel_prompt_text += f", budget={budget_filter}"
            if amenities_filter:
                hotel_prompt_text += f", amenities='{amenities_filter}'"
            
            hotel_prompt = Message(role="user", parts=[Part(text=hotel_prompt_text)])
            hotels_text = ""
            try:
                for event in hotel_runner.run(user_id=user_id, session_id=f"{session_id_base}_hotel", new_message=hotel_prompt, run_config=run_config):
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                hotels_text += part.text
            except Exception as e:
                print(f"Erreur hotel: {e}")
            
            hotel_pattern = r"-\s+([^à]+)\s+à\s+([^p]+)\s+pour\s+([\d.]+)€/nuit\s+\(Dispo:\s+([^a]+)\s+au\s+([^,]+),\s+Services:\s+(.*)\)"
            for m in re.finditer(hotel_pattern, hotels_text):
                found_amenities = m.group(6).strip() if m.group(6) else ""
                if found_amenities and found_amenities.endswith(")"):
                    found_amenities = found_amenities[:-1]
                hotels_data.append({"name": m.group(1).strip(), "city": m.group(2).strip(), "price": float(m.group(3)), "available_start": m.group(4).strip(), "available_end": m.group(5).strip(), "amenities": found_amenities})
        
        # FLIGHTS
        if call_flights:
            yield f"data: {json.dumps({'type': 'log', 'message': '✈️ Recherche vols...'})}\\n\\n"
            flight_runner = Runner(agent=flight_agent, app_name=app_name, session_service=session_service)
            
            budget_match = re.search(r'(\d+)\s*€', message)
            max_price = int(budget_match.group(1)) if budget_match else None
            
            flight_prompt_text = f"Appelle search_flights avec origin='{origin}', destination='{destination or ''}'"
            if max_price:
                flight_prompt_text += f", max_price={max_price}"
            
            flight_prompt = Message(role="user", parts=[Part(text=flight_prompt_text)])
            flights_text = ""
            try:
                for event in flight_runner.run(user_id=user_id, session_id=f"{session_id_base}_flight", new_message=flight_prompt, run_config=run_config):
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                flights_text += part.text
            except Exception as e:
                print(f"Erreur flight: {e}")
            
            flight_pattern = r"-\s+([^(]+)\([^)]+\)\s*:\s*([^|]+)\s*\|\s*départ\s+([^a]+)\s+arrivée\s+([^p]+)\s+pour\s+([\d.]+)€"
            for m in re.finditer(flight_pattern, flights_text):
                flights_data.append({"airline": m.group(1).strip(), "route": m.group(2).strip(), "departure": m.group(3).strip(), "arrival": m.group(4).strip(), "price": float(m.group(5))})
        
        yield f"data: {json.dumps({'type': 'response', 'message': response_message})}\\n\\n"
        yield f"data: {json.dumps({'type': 'results', 'flights': flights_data, 'activities': activities_data, 'hotels': hotels_data})}\\n\\n"
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Terminé !'})}\\n\\n"
        print(f"📊 CHAT: {len(flights_data)} vols | {len(activities_data)} act | {len(hotels_data)} hôtels")
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


 
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)