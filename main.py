from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import os
import json
import asyncio
import re
import sys
from dotenv import load_dotenv

# Fix Windows: UTF-8 encoding pour les emojis
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# --- MILESTONE 3 : On importe les deux supervisors ---
from test_agent.agent import root_agent, refine_supervisor

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
session_results = {}

# Compteur pour générer des session_id uniques (éviter les conflits de session)
_session_counter = 0


def _next_session_id(prefix: str) -> str:
    global _session_counter
    _session_counter += 1
    return f"{prefix}_{_session_counter}"


# ────────────────────────────────────────────
# FONCTIONS DE PARSING (réutilisées partout)
# ────────────────────────────────────────────

def _extract_section(text: str, start_marker: str, end_marker: str) -> str:
    """Extrait le texte entre deux balises ### DEBUT_X ### et ### FIN_X ###.
    Nettoie aussi les blocs JSON/markdown que le LLM pourrait ajouter."""
    pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return ""
    
    raw = m.group(1).strip()
    
    # Si le LLM a wrappé dans du ```json ... ```, extraire le contenu
    # et essayer de récupérer le texte brut depuis le JSON
    if "```json" in raw or '{"' in raw:
        import json as _json
        # Enlever les blocs ```json ... ```
        cleaned = re.sub(r'```json\s*', '', raw)
        cleaned = re.sub(r'```\s*', '', cleaned)
        
        # Essayer de parser chaque bloc JSON et extraire "result"
        extracted_parts = []
        for json_match in re.finditer(r'\{[^{}]*"result"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}', cleaned, re.DOTALL):
            # Unescape le texte JSON
            result_text = json_match.group(1)
            result_text = result_text.replace('\\n', '\n').replace("\\'", "'").replace('\\"', '"')
            extracted_parts.append(result_text)
        
        # Aussi essayer avec des JSON imbriqués type {"key": {"result": "..."}}
        for json_block in re.finditer(r'\{[^{]*?\{[^}]*"result"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}[^}]*\}', cleaned, re.DOTALL):
            result_text = json_block.group(1)
            result_text = result_text.replace('\\n', '\n').replace("\\'", "'").replace('\\"', '"')
            if result_text not in extracted_parts:
                extracted_parts.append(result_text)
        
        if extracted_parts:
            return '\n'.join(extracted_parts).strip()
        
        # Si on n'a pas trouvé de "result", retourner le texte nettoyé des balises markdown
        return cleaned.strip()
    
    return raw


def _parse_flights(text: str) -> list:
    """
    Parse les vols depuis le texte retourné par l'agent.
    Format attendu: - Airline (FlightNum) : Origin -> Dest | départ TIME arrivée TIME pour PRICE€
    Version robuste avec fallback.
    """
    flights = []

    # --- DEDUPLICATION ---
    unique_keys = set()
    deduplicated_flights = []

    # Regex principale
    flight_pattern = (
        r"-\s+(.+?)\s+\(([^)]+)\)\s*:\s*(.+?)\s*->\s*(.+?)\s*\|\s*"
        r"[dé]*[eé]?part\s+(.+?)\s+arriv[ée]+e?\s+(.+?)\s+pour\s+([\d.,]+)\s*€"
    )
    for m in re.finditer(flight_pattern, text, re.IGNORECASE):
        item = {
            "airline": f"{m.group(1).strip()} ({m.group(2).strip()})",
            "origin": m.group(3).strip(),
            "destination": m.group(4).strip(),
            "departure": m.group(5).strip(),
            "arrival": m.group(6).strip(),
            "price": m.group(7).strip().replace(",", ".")
        }
        key = f"{item['airline']}|{item['departure']}|{item['arrival']}"
        if key not in unique_keys:
            unique_keys.add(key)
            deduplicated_flights.append(item)

    if deduplicated_flights:
        return deduplicated_flights

    # --- Fallback : regex plus souple (ligne par ligne) ---
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("-"):
            continue

        # Tenter d'extraire au moins airline + prix
        price_match = re.search(r"([\d.,]+)\s*€", line)
        if not price_match:
            continue

        price = price_match.group(1).replace(",", ".")

        # Extraire airline (tout avant la parenthèse ou le ":")
        airline_match = re.match(r"-\s+(.+?)(?:\s*\(|\s*:)", line)
        airline = airline_match.group(1).strip() if airline_match else "Vol"

        # Extraire flight number si présent
        fn_match = re.search(r"\(([^)]+)\)", line)
        if fn_match:
            airline = f"{airline} ({fn_match.group(1).strip()})"

        # Extraire departure time si présent
        dep_match = re.search(r"[dé]*[eé]?part\s+(\S+(?:\s+\S+)?)", line, re.IGNORECASE)
        departure = dep_match.group(1).strip() if dep_match else "N/A"

        item = {
            "airline": airline,
            "origin": "",
            "destination": "",
            "departure": departure,
            "arrival": "",
            "price": price
        }
        
        # Clé un peu plus simple pour le fallback
        key = f"{item['airline']}|{item['departure']}|{item['price']}"
        if key not in unique_keys:
            unique_keys.add(key)
            deduplicated_flights.append(item)

    return deduplicated_flights


def _parse_activities(text: str) -> list:
    """
    Parse les activités/restaurants depuis le texte retourné par l'agent.
    Format attendu: Type, Nom, Prix€, Description
    Version robuste avec fallback.
    """
    activities = []

    # --- DEDUPLICATION ---
    unique_keys = set()
    deduplicated_activities = []

    # --- Regex principale ---
    act_pattern = r"(Activit[ée]|Restaurant)\s*,\s*([^,]+?)\s*,\s*([\d.,]+)\s*€\s*,\s*(.*)"
    for m in re.finditer(act_pattern, text, re.IGNORECASE):
        act_type = m.group(1).strip()
        # Normaliser le type
        if act_type.lower().startswith("activit"):
            act_type = "Activité"
        else:
            act_type = "Restaurant"

        item = {
            "type": act_type,
            "name": m.group(2).strip(),
            "price": m.group(3).strip().replace(",", "."),
            "description": m.group(4).strip()
        }
        
        key = f"{item['name']}|{item['price']}"
        if key not in unique_keys:
            unique_keys.add(key)
            deduplicated_activities.append(item)

    if deduplicated_activities:
        return deduplicated_activities

    # --- Fallback : lignes avec un prix ---
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Exclure les lignes qui sont clairement des hôtels
        lower_line = line.lower()
        if any(h in lower_line for h in ["€/nuit", "dispo:", "dispo :", "services:", "services :"]):
            continue

        price_match = re.search(r"([\d.,]+)\s*€", line)
        if not price_match:
            continue

        price = price_match.group(1).replace(",", ".")

        # Deviner le type
        lower = line.lower()
        if any(w in lower for w in ["restaurant", "cuisine", "menu", "plat", "gastronomie"]):
            act_type = "Restaurant"
        else:
            act_type = "Activité"

        # Le reste = nom + description
        # Enlever le prix du texte pour récupérer le nom
        clean = re.sub(r"[\d.,]+\s*€/?(?:nuit)?", "", line).strip(" -•·")
        parts = [p.strip() for p in clean.split(",", 1)]
        name = parts[0] if parts else line
        description = parts[1] if len(parts) > 1 else ""

        if name:
            item = {
                "type": act_type,
                "name": name,
                "price": price,
                "description": description
            }
            key = f"{item['name']}|{item['price']}"
            if key not in unique_keys:
                unique_keys.add(key)
                deduplicated_activities.append(item)

    return deduplicated_activities


def _parse_hotels(text: str) -> list:
    """
    Parse les hôtels depuis le texte retourné par l'agent.
    Format attendu: - Nom à Ville pour Prix€/nuit (Dispo: start au end, Services: ...)
    Version robuste avec fallback.
    """
    # --- DEDUPLICATION ---
    unique_keys = set()
    deduplicated_hotels = []

    # Regex principale
    hotel_pattern = (
        r"-\s+(.+?)\s+[àa]\s+(.+?)\s+pour\s+([\d.,]+)\s*€/nuit\s*"
        r"\(Dispo\s*:\s*(.+?)\s+au\s+(.+?)\s*,\s*Services?\s*:\s*(.*?)\s*\)"
    )
    for m in re.finditer(hotel_pattern, text, re.IGNORECASE):
        services = m.group(6).strip()
        if services.endswith(")"): services = services[:-1].strip()

        item = {
            "name": m.group(1).strip(),
            "city": m.group(2).strip(),
            "price": m.group(3).strip().replace(",", "."),
            "available_start": m.group(4).strip(),
            "available_end": m.group(5).strip(),
            "amenities": services
        }
        
        key = f"{item['name']}|{item['city']}"
        if key not in unique_keys:
            unique_keys.add(key)
            deduplicated_hotels.append(item)

    if deduplicated_hotels:
        return deduplicated_hotels

    # --- Fallback ---
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("-") or "€/nuit" not in line:
            continue

        price_match = re.search(r"([\d.,]+)\s*€/nuit", line)
        if not price_match:
            continue

        price = price_match.group(1).replace(",", ".")
        # Extraire le nom (entre "- " et " à " ou le premier séparateur)
        name_match = re.match(r"-\s+(.+?)(?:\s+[àa]\s+|\s+pour\s+|\s*\()", line)
        name = name_match.group(1).strip() if name_match else "Hôtel"

        # Extraire la ville (après "à" et avant "pour")
        city_match = re.search(r"[àa]\s+(.+?)\s+pour", line, re.IGNORECASE)
        city = city_match.group(1).strip() if city_match else ""

        # Extraire les dates
        date_match = re.search(r"Dispo\s*:\s*(\S+)\s+au\s+(\S+)", line, re.IGNORECASE)
        available_start = date_match.group(1) if date_match else ""
        available_end = date_match.group(2) if date_match else ""

        # Tentative d'extraction services
        services = ""
        serv_match = re.search(r"Services?\s*:\s*(.*?)(?:\)|$)", line, re.IGNORECASE)
        if serv_match:
            services = serv_match.group(1).strip()

        item = {
            "name": name,
            "city": city,
            "price": price,
            "available_start": available_start,
            "available_end": available_end,
            "amenities": services
        }
        
        key = f"{item['name']}|{item['city']}"
        if key not in unique_keys:
            unique_keys.add(key)
            deduplicated_hotels.append(item)

    return deduplicated_hotels


async def _run_supervisor_streaming(prompt_text: str, agent=None):
    """
    Async generator : yield des SSE log events pendant l'exécution du supervisor,
    puis yield le texte final en dernier (marqué type='supervisor_done').
    agent: l'agent à utiliser (root_agent par défaut, refine_supervisor pour le chat)
    """
    if agent is None:
        agent = root_agent

    app_name = "travel_agent"
    user_id = "user_stream"
    session_id = _next_session_id("supervisor")

    try:
        await session_service.create_session(
            user_id=user_id, session_id=session_id, app_name=app_name
        )
    except Exception:
        pass

    runner = Runner(
        agent=agent, app_name=app_name, session_service=session_service
    )
    run_config = RunConfig(max_llm_calls=30)

    prompt = Message(role="user", parts=[Part(text=prompt_text)])

    full_text = ""
    tool_responses_text = ""
    event_count = 0

    print("\n" + "=" * 60)
    print("  SUPERVISOR - DEBUT D'EXECUTION")
    print("=" * 60)

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id,
        new_message=prompt, run_config=run_config
    ):
        event_count += 1
        author = getattr(event, 'author', '???')
        print(f"\n--- Event #{event_count} | Auteur: {author} ---")

        if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts') and event.content.parts:
            for part in event.content.parts:

                # Tool call -> stream au navigateur
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    func_name = getattr(fc, 'name', '???')
                    func_args = getattr(fc, 'args', {})
                    print(f"  >> TOOL CALL: {func_name}({func_args})")

                    # Emoji par type d'outil
                    if 'flight' in func_name.lower():
                        icon = "plane"
                    elif 'hotel' in func_name.lower():
                        icon = "hotel"
                    elif 'restaurant' in func_name.lower():
                        icon = "fork"
                    elif 'activit' in func_name.lower():
                        icon = "activity"
                    elif 'transfer' in func_name.lower():
                        icon = "transfer"
                    else:
                        icon = "tool"

                    ICONS = {
                        "plane": "\u2708\ufe0f",
                        "hotel": "\U0001f3e8",
                        "fork": "\U0001f374",
                        "activity": "\U0001f3ad",
                        "transfer": "\U0001f500",
                        "tool": "\U0001f527",
                    }
                    emoji = ICONS.get(icon, "\U0001f527")

                    # Message lisible pour le navigateur
                    args_str = ", ".join(f"{k}={v}" for k, v in func_args.items()) if func_args else ""
                    log_msg = f"{emoji} {author} appelle {func_name}({args_str})"
                    yield f"data: {json.dumps({'type': 'tool', 'message': log_msg}, ensure_ascii=False)}\n\n"

                # Tool response -> stream au navigateur
                if hasattr(part, 'function_response') and part.function_response:
                    fr = part.function_response
                    resp_name = getattr(fr, 'name', '???')
                    resp_data = getattr(fr, 'response', '')
                    resp_str = str(resp_data)
                    if len(resp_str) > 200:
                        resp_str = resp_str[:200] + "..."
                    print(f"  << TOOL RESPONSE ({resp_name}): {resp_str}")

                    # Capturer le résultat des outils métier (fallback si le sub-agent ne génère pas de texte)
                    if resp_name not in ('transfer_to_agent',) and isinstance(resp_data, dict):
                        result_val = resp_data.get('result', '')
                        if result_val and isinstance(result_val, str):
                            tool_responses_text += result_val + "\n"

                    yield f"data: {json.dumps({'type': 'log', 'message': f'Resultat de {resp_name} recu'}, ensure_ascii=False)}\n\n"

                # Texte normal
                if hasattr(part, 'text') and part.text:
                    text_preview = part.text[:200] + "..." if len(part.text) > 200 else part.text
                    print(f"  TEXT [{author}]: {text_preview}")
                    full_text += part.text

    # Toujours ajouter les tool_responses au full_text pour que les parsers
    # puissent matcher le format "- Nom à Ville pour Prix€/nuit (...)" même
    # quand l'agent reformate tout en texte inline sans les "- " en préfixe.
    if tool_responses_text.strip():
        if full_text.strip():
            full_text = full_text.rstrip() + "\n\n" + tool_responses_text.strip()
        else:
            print("WARN: full_text vide, utilisation des tool_responses comme fallback")
            full_text = tool_responses_text.strip()

    print("\n" + "=" * 60)
    print(f"  SUPERVISOR - FIN ({event_count} events)")
    print(f"  Reponse totale: {len(full_text)} caracteres")
    print("=" * 60 + "\n")

    # Dernier yield = le texte complet
    yield f"__DONE__{full_text}"


# ────────────────────────────────────────────
# ROUTES
# ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stream_search")
async def stream_search(
    request: Request,
    origin: str,
    destination: str,
    departure_date: str = None,
    budget_max: str = None,
    airline: str = None,
    activities: str = None,
    hotel_budget_max: str = None,
    amenities: str = None
):
    print(f"\n>>> NOUVELLE REQUETE : {origin} -> {destination}")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'log', 'message': 'Connexion au Supervisor...'})}\n\n"
        await asyncio.sleep(0.3)

        # -- Construire UN SEUL prompt naturel pour le Supervisor --
        prompt_parts = [f"Je veux voyager de {origin} vers {destination}."]

        if departure_date:
            prompt_parts.append(f"Date souhaitee : {departure_date}.")
            
            # --- INSTRUCTION SÉQUENTIELLE OBLIGATOIRE (Si date fixée) ---
            prompt_parts.append("""
            IMPORTANT - STRATÉGIE D'EXECUTION OBLIGATOIRE :
            ÉTAPE 1 : Appelle UNIQUEMENT search_flights (et activities/restaurants).
            ÉTAPE 2 : ATTENDS le résultat de search_flights.
            ÉTAPE 3 : Une fois que tu as la date d'arrivée du vol, appelle search_hotels avec CETTE date précise.
            NE DEVINE PAS la date de l'hôtel. N'appelle PAS search_hotels tant que tu n'as pas le vol.
            """)
        else:
            # --- INSTRUCTION FLEXIBLE (Si aucune date fixée) ---
            prompt_parts.append("""
            STRATÉGIE FLEXIBLE :
            Aucune date précise n'est fixée. Cherche des vols et des hôtels disponibles globalement pour donner des idées.
            N'hésite pas à proposer plusieurs options d'hôtels, même si les dates ne correspondent pas exactement à un vol précis.
            """)
        
        if activities and activities.strip():
            # Si l'utilisateur a spécifié quelque chose (ex: "restaurant"), on filtre
            prompt_parts.append(f"Je cherche spécifiquement : {activities}.")
        else :
            # Si le champ est vide, on veut TOUT (activités ET restaurants)
            prompt_parts.append(f"Trouve-moi des activités touristiques ET des restaurants locaux.")
        if hotel_budget_max:
            prompt_parts.append(f"Budget hotel max : {hotel_budget_max}EUR/nuit.")
        if amenities and amenities.strip():
            prompt_parts.append(f"Services hotel souhaites : {amenities}.")
        else:
            prompt_parts.append(f"Tous les hotels sont attendus.")

        prompt_text = " ".join(prompt_parts)
        print(f"PROMPT SUPERVISOR: {prompt_text}")

        yield f"data: {json.dumps({'type': 'tool', 'message': 'Le Supervisor delegue aux agents specialises...'})}\n\n"

        # -- Appel streaming au Supervisor --
        full_response = ""
        try:
            async for sse_or_done in _run_supervisor_streaming(prompt_text):
                if sse_or_done.startswith("__DONE__"):
                    full_response = sse_or_done[8:]  # Enlever le prefix __DONE__
                else:
                    yield sse_or_done  # Forward les SSE events au navigateur
        except Exception as e:
            full_response = f"Erreur supervisor: {e}"
            print(f"ERREUR SUPERVISOR: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'log', 'message': f'Erreur: {e}'})}\n\n"

        print(f"REPONSE SUPERVISOR:\n{full_response}\n---")

        # -- Extraction des sections via les markers --
        flights_text = _extract_section(full_response, "### DEBUT_VOLS ###", "### FIN_VOLS ###")
        activities_text = _extract_section(full_response, "### DEBUT_ACTIVITES ###", "### FIN_ACTIVITES ###")
        # Le supervisor peut créer une section RESTAURANTS séparée
        restaurants_text = _extract_section(full_response, "### DEBUT_RESTAURANTS ###", "### FIN_RESTAURANTS ###")
        if restaurants_text:
            activities_text = (activities_text + "\n" + restaurants_text).strip()
        hotels_text = _extract_section(full_response, "### DEBUT_HOTELS ###", "### FIN_HOTELS ###")

        # Si pas de markers, on essaie de parser la reponse brute entiere
        if not flights_text and not activities_text and not hotels_text:
            print("WARN: Aucun marker ### DEBUT/FIN ### trouve, parsing sur la reponse brute")
            flights_text = full_response
            activities_text = full_response
            hotels_text = full_response

        # -- Parsing --
        flights = _parse_flights(flights_text)
        act_list = _parse_activities(activities_text)
        hotels_list = _parse_hotels(hotels_text)

        yield f"data: {json.dumps({'type': 'log', 'message': f'Resultats : {len(flights)} Vols, {len(act_list)} Activites, {len(hotels_list)} Hotels'})}\n\n"
        print(f"STATS : {len(flights)} Vols | {len(act_list)} Activites | {len(hotels_list)} Hotels")

        # Debug: si rien n'a été parsé, afficher les premières lignes
        if not flights and not act_list and not hotels_list:
            print("WARN: Aucun resultat parse! Apercu de la reponse:")
            for i, line in enumerate(full_response.split("\n")[:20]):
                print(f"  L{i}: {line}")

        session_key = f"{origin}_{destination}"
        session_results[session_key] = {
            'flights': flights,
            'activities': act_list,
            'hotels': hotels_list
        }

        final_html = templates.get_template("results.html").render({
            "request": request,
            "response": full_response,
            "flights": flights,
            "activities": act_list,
            "hotels": hotels_list,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date
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
    return await stream_search(request, origin, destination, preferences)


@app.get("/chat_refine")
async def chat_refine(request: Request, message: str, origin: str, destination: str, date: str = None):
    print(f"\nCHAT REFINE: {message} (Date ctx: {date})")

    async def event_generator():
        target = destination if destination else origin

        date_context = f"Date du voyage initialement prévue : {date}." if date else "Aucune date précise n'est fixée."

        prompt_text = (
            f"CONTEXTE : Voyage de {origin} vers {target}. {date_context} "
            f"DEMANDE DE RAFFINEMENT : \"{message}\". "
            f"Si c'est une demande d'hôtel ou de vol, utilise la date ci-dessus si pertinente. "
            f"Transfère au bon agent spécialisé."
        )

        yield f"data: {json.dumps({'type': 'log', 'message': 'Le Refine Supervisor route vers le bon agent...'})}\n\n"

        # -- Appel streaming au Refine Supervisor (MULTI-AGENT via transfer_to_agent) --
        full_response = ""
        try:
            async for sse_or_done in _run_supervisor_streaming(prompt_text, agent=refine_supervisor):
                if sse_or_done.startswith("__DONE__"):
                    full_response = sse_or_done[8:]
                else:
                    yield sse_or_done
        except Exception as e:
            full_response = f"Erreur supervisor: {e}"
            print(f"ERREUR SUPERVISOR: {e}")

        print(f"CHAT SUPERVISOR:\n{full_response}\n---")

        # -- Extraction des sections --
        flights_text = _extract_section(full_response, "### DEBUT_VOLS ###", "### FIN_VOLS ###")
        activities_text = _extract_section(full_response, "### DEBUT_ACTIVITES ###", "### FIN_ACTIVITES ###")
        restaurants_text = _extract_section(full_response, "### DEBUT_RESTAURANTS ###", "### FIN_RESTAURANTS ###")
        if restaurants_text:
            activities_text = (activities_text + "\n" + restaurants_text).strip()
        hotels_text = _extract_section(full_response, "### DEBUT_HOTELS ###", "### FIN_HOTELS ###")

        # Parsing : UNIQUEMENT les sections avec markers
        # Si aucun marker n'est trouvé, on essaie de deviner intelligemment quel parser utiliser
        # en analysant le contenu de la réponse
        if flights_text or activities_text or hotels_text:
            # Cas normal : on a des markers, on parse uniquement les sections présentes
            flights_data = _parse_flights(flights_text) if flights_text else []
            activities_data = _parse_activities(activities_text) if activities_text else []
            hotels_data = _parse_hotels(hotels_text) if hotels_text else []
        else:
            # Aucun marker trouvé : l'agent a renvoyé du texte brut
            # On devine quel type de données c'est en regardant le contenu
            lower_response = full_response.lower()
            
            # Compter les indicateurs de chaque type
            has_flight_indicators = any(word in lower_response for word in ["vol", "départ", "arrivée", "flight", "airline", "->", "→"])
            has_hotel_indicators = any(word in lower_response for word in ["hôtel", "hotel", "€/nuit", "dispo:", "services:"])
            has_activity_indicators = any(word in lower_response for word in ["activité", "restaurant", "musée", "visite", "cuisine"])
            
            # Parser uniquement ce qui semble être présent
            flights_data = _parse_flights(full_response) if has_flight_indicators else []
            activities_data = _parse_activities(full_response) if has_activity_indicators else []
            hotels_data = _parse_hotels(full_response) if has_hotel_indicators else []

        # Message dynamique selon ce qui a été trouvé
        parts = []
        if flights_data:
            parts.append(f"{len(flights_data)} vol(s)")
        if activities_data:
            parts.append(f"{len(activities_data)} activité(s)/restaurant(s)")
        if hotels_data:
            parts.append(f"{len(hotels_data)} hôtel(s)")
        
        if parts:
            response_message = f"J'ai mis à jour les résultats : {', '.join(parts)} trouvé(s) !"
        else:
            response_message = "Désolé, je n'ai rien trouvé pour cette recherche."

        yield f"data: {json.dumps({'type': 'response', 'message': response_message})}\n\n"

        # N'envoyer au front QUE les catégories non-vides (pour ne pas écraser les résultats existants)
        results_payload = {}
        if flights_data:
            results_payload['flights'] = flights_data
        if activities_data:
            results_payload['activities'] = activities_data
        if hotels_data:
            results_payload['hotels'] = hotels_data
        yield f"data: {json.dumps({'type': 'results', **results_payload})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Termine !'})}\n\n"

        print(f"CHAT: {len(flights_data)} vols | {len(activities_data)} act | {len(hotels_data)} hotels")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)