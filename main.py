import os
import json
import random
import requests
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Importa configurazione
try:
    from config import GOOGLE_SHEETS_URL, ENABLE_GOOGLE_SHEETS
except ImportError:
    GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
    ENABLE_GOOGLE_SHEETS = True

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OPTIONS_PATH = os.path.join(DATA_DIR, 'options.json')
SCORES_PATH = os.path.join(DATA_DIR, 'scores.json')
MAPPING_PATH = os.path.join(DATA_DIR, 'mapping.json')

app = FastAPI()

# Serve static files from /static
app.mount("/static", StaticFiles(directory=PROJECT_ROOT, html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(path: str, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def weighted_choice(options: list, scores: dict) -> Optional[str]:
    weights = []
    for code in options:
        score = scores.get(code, 0)
        if score > 0:
            w = 3
        elif score < 0:
            w = 0.5
        else:
            w = 1
        weights.append(w)
    return random.choices(options, weights=weights, k=1)[0] if options else None

def get_mapping() -> Optional[Dict[str, str]]:
    if os.path.exists(MAPPING_PATH):
        return load_json(MAPPING_PATH, {})
    return None

def codes_to_text(codes: List[str], mapping: Optional[Dict[str, str]]) -> List[str]:
    if not mapping:
        return codes
    return [mapping.get(code, code) for code in codes]

def get_label(mapping, code):
    val = mapping.get(code, code)
    if isinstance(val, dict):
        return val.get('label', code)
    return val

def spin(locked: dict, level: str) -> dict:
    options = load_json(OPTIONS_PATH, {})
    scores = load_json(SCORES_PATH, {})
    mapping = get_mapping() or {}
    result = {}
    # 1. Estrai azione (o usa lock)
    action_codes = options.get('azione', [])
    if 'azione' in locked and locked['azione'] in action_codes:
        action_choice = locked['azione']
    else:
        action_choice = weighted_choice(action_codes, scores)
    result['azione'] = action_choice if action_choice else ''
    # 2. Estrai luogo compatibile (o usa lock)
    luogo_codes = options.get('luogo', [])
    def is_compatible(action_code, luogo_code):
        def get_list(code, key):
            val = mapping.get(code, {})
            if isinstance(val, dict):
                return val.get(key, [])
            return []
        needs = get_list(action_code, 'needs')
        supports = get_list(luogo_code, 'supports')
        return all(n in supports for n in needs)
    if 'luogo' in locked and locked['luogo'] in luogo_codes:
        luogo_choice = locked['luogo']
        # Se lock, forzo compatibilità
        if not is_compatible(action_choice, luogo_choice):
            # Se non compatibile, fallback: prendi uno compatibile
            compatibili = [l for l in luogo_codes if is_compatible(action_choice, l)]
            luogo_choice = compatibili[0] if compatibili else luogo_codes[0] if luogo_codes else ''
    else:
        compatibili = [l for l in luogo_codes if is_compatible(action_choice, l)]
        if compatibili:
            luogo_choice = weighted_choice(compatibili, scores)
        else:
            luogo_choice = weighted_choice(luogo_codes, scores)
    result['luogo'] = luogo_choice if luogo_choice else ''
    # 3. Estrai le altre categorie normalmente
    for cat, codes in options.items():
        if cat in ('azione', 'luogo'):
            continue
        filtered_codes = codes
        if level and cat == "energy":
            filtered_codes = [c for c in codes if c.startswith(f"int_{level[-1]}") or c.startswith("int_any")] or codes
        if cat in locked and locked[cat] in codes:
            code = locked[cat]
        else:
            code = weighted_choice(filtered_codes, scores)
        result[cat] = code if code is not None else ""
    return result

@app.get("/spin")
async def spin_get():
    options = load_json(OPTIONS_PATH, {})
    scores = load_json(SCORES_PATH, {})
    mapping = get_mapping()
    
    print("Loaded options:", options.keys())  # Debug log
    
    result = {}
    readable = {}
    for cat, codes in options.items():
        code = weighted_choice(codes, scores)
        result[cat] = code if code is not None else ""
        readable[cat] = get_label(mapping, code) if mapping and code is not None else (code if code is not None else "")
    
    response_data = {
        "codes": result,
        "readable": readable,
        "options": options
    }
    print("Sending response:", response_data.keys())  # Debug log
    return response_data

@app.post("/spin")
async def spin_post(body: Dict = Body(...)):
    payload = body if isinstance(body, dict) else {}
    level    = payload.get("level", "")
    spinPart = payload.get("spinPart", False)
    locked   = payload.get("locked", {})

    # Default coppia
    if not spinPart:
        # NON includere 'partecipanti' nei risultati visibili, ma restituisci comunque la chiave
        locked["partecipanti"] = "part_001"

    result = spin(locked, level)

    # NON rimuovere la chiave 'partecipanti' dal dict da inviare!
    # if not spinPart and "partecipanti" in result:
    #     result.pop("partecipanti")

    mapping = get_mapping()
    options = load_json(OPTIONS_PATH, {})
    
    # Crea la combinazione completa per Google Sheets
    combination_text = ""
    if mapping:
        for cat, code in result.items():
            if code and cat != "partecipanti":
                label = get_label(mapping, code)
                combination_text += f"{cat}: {label}\n"
    
    # Invia ogni carta a Google Sheets
    for cat, code in result.items():
        if code and cat != "partecipanti":
            label = get_label(mapping, code) if mapping else code
            send_to_google_sheets(cat, code, label, "Generated", combination_text)
    
    return {
        "codes": result,
        "readable": {cat: get_label(mapping, code) if mapping and code is not None else (code if code is not None else "") for cat, code in result.items()},
        "options": options
    }

@app.post("/feedback")
async def feedback_post(body: Dict = Body(...)):
    codes = body.get("codes", {})
    like = body.get("like", True)
    scores = load_json(SCORES_PATH, {})
    for code in codes.values():
        if code is not None:
            scores[code] = scores.get(code, 0) + (1 if like else -1)
    save_json(SCORES_PATH, scores)
    return {"ok": True, "scores": scores}

@app.post("/card-feedback")
async def card_feedback_post(body: Dict = Body(...)):
    category = body.get("category")
    code = body.get("code")
    like = body.get("like", True)
    combination = body.get("combination", "")  # Aggiungo il campo combinazione
    
    if not category or not code:
        return JSONResponse({"error": "Missing category or code"}, status_code=400)
        
    scores = load_json(SCORES_PATH, {})
    scores[code] = scores.get(code, 0) + (1 if like else -1)
    save_json(SCORES_PATH, scores)
    
    # Invia a Google Sheets
    label = get_label(get_mapping(), code)
    feedback_text = "Like" if like else "Dislike"
    send_to_google_sheets(category, code, label, feedback_text, combination)
    
    return {"ok": True, "score": scores[code]}

def send_to_google_sheets(category: str, code: str, label: str, feedback: str, combination: str = ""):
    """
    Invia dati a Google Sheets tramite Apps Script
    """
    if not ENABLE_GOOGLE_SHEETS:
        return True  # Se disabilitato, ritorna sempre successo
        
    try:
        # URL del tuo Google Apps Script (da sostituire con quello reale)
        script_url = GOOGLE_SHEETS_URL
        
        # Prepara i dati
        data = {
            "category": category,
            "code": code,
            "label": label,
            "feedback": feedback,
            "combination": combination
        }
        
        # Invia la richiesta
        response = requests.post(script_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"Dati inviati a Google Sheets: {category} - {code} - {feedback}")
                return True
            else:
                print(f"Errore Google Sheets: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"Errore HTTP Google Sheets: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Errore nell'invio a Google Sheets: {e}")
        return False

# Serve index.html at root
@app.get("/")
async def root():
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) 