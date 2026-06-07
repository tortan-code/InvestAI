# Deploy-guide for InvestAI v9

## 1. GitHub

Opprett repo på GitHub, for eksempel:

```text
InvestAI
```

Last opp alle filene fra ZIP-mappen. `app.py` og `requirements.txt` må ligge i root/hovednivå.

## 2. Streamlit Cloud

Gå til Streamlit Community Cloud og velg:

```text
Repository: InvestAI
Branch: main
Main file path: app.py
```

Trykk Deploy.

## 3. Vanlige feil

### Appen finner ikke app.py
Sjekk at `app.py` ligger direkte i repoet, ikke inne i en ekstra mappe.

### ModuleNotFoundError
Sjekk at pakken står i `requirements.txt`.

### Datafil mangler
Sjekk at CSV-filene ligger sammen med `app.py`.

### Streamlit viser rød feil uten detaljer
Åpne Streamlit Cloud → Manage app → Logs. Kopier feilen og lim den inn i ChatGPT.

## 4. Anbefalt GitHub-struktur

```text
InvestAI/
├── app.py
├── requirements.txt
├── README.md
├── DEPLOY_GUIDE.md
├── oslo_universe.csv
├── watchlist.csv
├── portfolio.csv
├── earnings_calendar.csv
├── insider_watch.csv
├── notes.csv
├── .gitignore
└── .streamlit/
    └── config.toml
```
