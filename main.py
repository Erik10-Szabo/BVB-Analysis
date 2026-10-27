import os
import time
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="BVB Market Intelligence Terminal")

gemini_client = None
if os.getenv("GEMINI_API_KEY"):
    gemini_client = genai.Client()

ANALYSIS_CACHE = {}
CACHE_TTL_SECONDS = 1800

ALL_BVB_COMPANIES = [
    ("TLV", "Banca Transilvania S.A.", "Sector Bancar"),
    ("SNP", "OMV Petrom S.A.", "Energie & Petrol"),
    ("H2O", "SPEEH Hidroelectrica S.A.", "Energie Verde / Hidro"),
    ("SNG", "S.N.G.N. Romgaz S.A.", "Gaze Naturale"),
    ("SNN", "S.N. Nuclearelectrica S.A.", "Energie Nucleara"),
    ("BRD", "BRD - Groupe Societe Generale S.A.", "Sector Bancar"),
    ("DIGI", "Digi Communications N.V.", "Telecomunicatii"),
    ("EL", "Electrica S.A.", "Distributie & Furnizare Energie"),
    ("TGN", "S.N.T.G.N. Transgaz S.A.", "Transport Gaze Naturale"),
    ("TEL", "C.N.T.E.E. Transelectrica S.A.", "Transport Energie Electrica"),
    ("M", "MedLife S.A.", "Servicii Medicale Private"),
    ("ONE", "One United Properties S.A.", "Dezvoltare Imobiliara / Real Estate"),
    ("FP", "Fondul Proprietatea S.A.", "Fond de Investitii"),
    ("TTS", "Transport Trade Services S.A.", "Transport Fluvial & Portuar"),
    ("PE", "Premier Energy PLC", "Furnizare Energie & Gaze"),
    ("AQ", "Aquila Part Prod Com S.A.", "Distributie & Logistica FMCG"),
    ("ATB", "Antibiotice S.A.", "Industria Farmaceutica"),
    ("TRP", "TeraPlast S.A.", "Productie Materiale de Constructii"),
    ("SFG", "Sphera Franchise Group S.A.", "Horeca / Restauration (KFC, Pizza Hut)"),
    ("COTE", "Conpet S.A.", "Transport Petrol prin Conducte"),
    ("BVB", "Bursa de Valori Bucuresti S.A.", "Infrastructura de Piata"),
    ("WINE", "Purcari Wineries Public Company Ltd.", "Productie Vinuri"),
    ("BIO", "Biofarm S.A.", "Industria Farmaceutica")
]

STOCKS_DB = {symbol: {"name": name, "sector": sector} for symbol, name, sector in ALL_BVB_COMPANIES}

class QuestionRequest(BaseModel):
    symbol: str
    user_question: str

@app.get("/api/stocks")
async def get_stocks():
    return STOCKS_DB

@app.post("/api/ask")
async def ask_gemini(req: QuestionRequest):
    sym = req.symbol.upper()
    user_q = req.user_question.strip()
    
    stock_info = STOCKS_DB.get(sym, {"name": sym, "sector": "Piata Reglementata BVB"})
    company_name = stock_info["name"]
    sector = stock_info["sector"]
    
    cache_key = f"{sym}:{user_q.lower()}"
    now_ts = time.time()
    
    if cache_key in ANALYSIS_CACHE:
        cached_text, timestamp = ANALYSIS_CACHE[cache_key]
        if now_ts - timestamp < CACHE_TTL_SECONDS:
            minutes_left = int((CACHE_TTL_SECONDS - (now_ts - timestamp)) / 60)
            return {"answer": cached_text + f"\n\n*(Cache: {minutes_left} min ramase)*"}

    now_str = datetime.now().strftime("%d.%m.%Y")

    prompt = f"""
    Esti un consultant financiar senior specializat pe Bursa de Valori Bucuresti (BVB) si Indicele BET.
    Data actuala: {now_str}.
    Compania: {company_name} ({sym}), Sector: {sector}.
    Cerinta: "{user_q}"

    Reguli obligatorii pentru raspuns (in limba romana simpla, fara diacritice):
    1. Ofera pretul curent si evolutia recenta a pretului pe BVB.
    2. Ofera rezultate financiare recente (Profit Net, Venituri, Dividende) de pe BVB.ro sau ZF.ro.
    3. Ofera o recomandare clara de tip: CUMPARA, HOLD sau VINDE, cu scurte argumente.
    """
    
    if not os.getenv("GEMINI_API_KEY") or not gemini_client:
        return {"answer": "Lipseste cheia GEMINI_API_KEY in setarile de pe Render."}

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"tools": [{"google_search": {}}]}
        )
        
        answer_text = response.text if response and response.text else "Fara raspuns."
        
        # Salvam in cache
        ANALYSIS_CACHE[cache_key] = (answer_text, now_ts)
        return {"answer": answer_text}

    except Exception:
        # Prindem orice eroare fara sa mai incercam conversii complicate care dau crash pe ASCII
        return {"answer": "Atentie: A aparut o limita de interogari sau o problema temporara de retea. Te rugam sa reincerci peste 1 minut."}


@app.get("/", response_class=HTMLResponse)
async def read_item():
    html_content = """
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BVB Market Intelligence Terminal</title>
        <style>
            :root { --bg-primary: #0f172a; --bg-secondary: #1e293b; --text-primary: #f8fafc; --text-secondary: #94a3b8; --accent: #38bdf8; --green: #22c55e; --border: #334155; }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-primary); color: var(--text-primary); padding: 25px; }
            .container { max-width: 1200px; margin: 0 auto; }
            header { border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
            h1 { color: var(--accent); font-size: 1.8rem; }
            .badge { background: #0284c7; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }
            .grid { display: grid; grid-template-columns: 350px 1fr; gap: 25px; }
            @media(max-width: 900px){ .grid { grid-template-columns: 1fr; } }
            .card { background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .card-title { font-size: 1.1rem; margin-bottom: 15px; border-bottom: 2px solid var(--accent); padding-bottom: 5px; display: inline-block; }
            label { display: block; margin-bottom: 8px; color: var(--text-secondary); font-size: 0.9rem; }
            select, input, button { width: 100%; padding: 12px; border-radius: 6px; border: 1px solid var(--border); background-color: #0f172a; color: var(--text-primary); font-size: 0.95rem; margin-bottom: 15px; }
            button { background-color: var(--accent); color: #0f172a; font-weight: bold; cursor: pointer; border: none; transition: 0.2s; }
            button:hover { opacity: 0.9; transform: translateY(-1px); }
            .result-box { background-color: #0f172a; border: 1px solid var(--border); border-radius: 6px; padding: 20px; min-height: 450px; white-space: pre-line; line-height: 1.6; font-size: 0.95rem; }
            .quick-btn { background-color: #334155; color: white; border: none; padding: 8px 12px; font-size: 0.85rem; border-radius: 4px; cursor: pointer; margin-bottom: 8px; width: 100%; text-align: left; }
            .quick-btn:hover { background-color: #475569; }
            .company-info-box { background: #0f172a; padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid var(--accent); }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>BVB Market Intelligence Terminal</h1>
                <span class="badge">Sursa: ZF.ro, Pret & Indicele BET</span>
            </header>
            
            <div class="grid">
                <div>
                    <div class="card">
                        <h2 class="card-title">Selecteaza Emitent BET</h2>
                        <label for="stockSelect">Companie listata:</label>
                        <select id="stockSelect"></select>

                        <div id="companyBox" class="company-info-box">
                            <strong id="compSymbol">TLV</strong> - <span id="compName">Banca Transilvania</span><br>
                            <small id="compSector" style="color: var(--text-secondary);">Sector Bancar</small>
                        </div>
                    </div>

                    <div class="card">
                        <h2 class="card-title">Analize Rapide</h2>
                        <button class="quick-btn" onclick="setQuestion('Ofera un raport complet cu evolutia pretului, rezultate financiare BVB, stiri ZF.ro si recomandare Cumpara/Hold/Vinde.')">📊 Raport Complet & Recomandare</button>
                        <button class="quick-btn" onclick="setQuestion('Care este evolutia recenta a pretului actiunii si ce tinta de pret indica analizele recente de pe ZF.ro?')">📈 Evolutie Pret & Tinta</button>
                        <button class="quick-btn" onclick="setQuestion('Este acum un moment bun de cumparat sau de vandut? Argumenteaza decizia (Cumpara/Hold/Vinde).')">🎯 Recomandare Cumpara / Vinde</button>
                        
                        <label style="margin-top: 15px;">Intrebare Personalizata:</label>
                        <input type="text" id="userQuestion" placeholder="Ex: Care e pretul actual si randamentul la dividend?" />
                        <button id="askBtn">Trimite Spre Analiza</button>
                    </div>
                </div>

                <div>
                    <div class="card">
                        <h2 class="card-title">Raport Financiar, Pret & Recomandare AI</h2>
                        <div id="resultBox" class="result-box">Selecteaza o companie pentru a genera raportul financiar cu evolutia pretului si recomandarea finala (CUMPARA / HOLD / VINDE).</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const stockSelect = document.getElementById('stockSelect');
            const compSymbol = document.getElementById('compSymbol');
            const compName = document.getElementById('compName');
            const compSector = document.getElementById('compSector');
            const userQuestion = document.getElementById('userQuestion');
            const askBtn = document.getElementById('askBtn');
            const resultBox = document.getElementById('resultBox');

            let stocksData = {};

            async function init() {
                try {
                    const res = await fetch('/api/stocks');
                    stocksData = await res.json();
                    
                    stockSelect.innerHTML = '';
                    for (const [symbol, data] of Object.entries(stocksData)) {
                        const opt = document.createElement('option');
                        opt.value = symbol;
                        opt.textContent = `${symbol} - ${data.name}`;
                        stockSelect.appendChild(opt);
                    }

                    if (Object.keys(stocksData).length > 0) {
                        stockSelect.value = 'TLV';
                        updateCompanyBox('TLV');
                    }
                } catch (e) {
                    console.error("Eroare la incarcare:", e);
                }
            }

            function updateCompanyBox(symbol) {
                const info = stocksData[symbol];
                if (info) {
                    compSymbol.textContent = symbol;
                    compName.textContent = info.name;
                    compSector.textContent = info.sector;
                }
            }

            function setQuestion(qText) { 
                userQuestion.value = qText; 
                triggerAsk();
            }

            stockSelect.addEventListener('change', (e) => { 
                updateCompanyBox(e.target.value); 
            });

            async function triggerAsk() {
                const symbol = stockSelect.value;
                const question = userQuestion.value.trim() || 'Ofera un raport complet cu evolutia pretului, rezultate financiare BVB, stiri ZF.ro si recomandare Cumpara/Hold/Vinde.';
                resultBox.innerHTML = "<em>Preluare date in curs... AI-ul verifica evolutia pretului, articolele ZF.ro si formuleaza recomandarea finala. Asteapta cateva secunde...</em>";
                try {
                    const res = await fetch('/api/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbol: symbol, user_question: question })
                    });
                    const data = await res.json();
                    resultBox.innerText = data.answer;
                } catch (e) {
                    resultBox.innerText = "Eroare la conexiunea cu serviciul de analiza.";
                }
            }

            askBtn.addEventListener('click', triggerAsk);

            init();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
