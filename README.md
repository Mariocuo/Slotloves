# SlotLove 🎰

Un'applicazione web per generare combinazioni casuali di categorie con feedback e sistema di pesi.

## Caratteristiche

- 🎲 Generazione casuale di combinazioni
- 🔒 Sistema di blocco delle scelte
- ⭐ Sistema di feedback per migliorare le scelte future
- 📱 Interfaccia moderna e responsive
- 🎯 Filtri per livello di difficoltà

## Tecnologie

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript vanilla
- **Deploy**: Compatibile con Heroku, Render, Railway

## Struttura del progetto

```
Slotlove/
├── data/
│   ├── mapping.json    # Mappatura codici -> etichette
│   ├── options.json    # Opzioni per categoria
│   └── scores.json     # Punteggi per feedback
├── main.py            # Server FastAPI
├── index.html         # Frontend
├── requirements.txt   # Dipendenze Python
├── Procfile          # Configurazione Heroku
└── runtime.txt       # Versione Python
```

## Deploy

### Render (Raccomandato)

1. Crea un account su [Render](https://render.com)
2. Connetti il tuo repository GitHub
3. Crea un nuovo "Web Service"
4. Seleziona il repository
5. Configura:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy!

### Heroku

1. Installa [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Crea un'app su Heroku
3. Esegui:
   ```bash
   heroku login
   heroku git:remote -a nome-tua-app
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

### Railway

1. Vai su [Railway](https://railway.app)
2. Connetti il repository GitHub
3. Deploy automatico!

## Sviluppo locale

```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia il server
python main.py

# Apri http://localhost:8000
```

## API Endpoints

- `GET /` - Frontend principale
- `GET /spin` - Genera una combinazione casuale
- `POST /spin` - Genera con parametri (locked, level)
- `POST /feedback` - Invia feedback per una combinazione
- `POST /card-feedback` - Invia feedback per una singola carta

## Licenza

MIT 