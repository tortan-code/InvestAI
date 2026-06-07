# InvestAI v9 – Professional GUI

Et gratis hobbyverktøy for aksjescreening, watchlist, porteføljeoversikt og ChatGPT-klare analyseprompter.

## Funksjoner

- Renere dashboard
- Aksjeprofil-side
- Bedre kortdesign
- Sektor- og faktorvisning
- Forklaringsmotor
- Red flag-panel
- Mobilvennlig layout
- Færre og mer relevante kolonner
- Bedre «kopier til ChatGPT»-flyt
- Bred Oslo Børs-screener via `oslo_universe.csv`

## Kjør lokalt

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy på Streamlit Cloud

1. Lag et GitHub-repo, for eksempel `InvestAI`.
2. Last opp alle filene i denne mappen til repoets hovednivå/root.
3. Gå til Streamlit Community Cloud.
4. Velg repoet ditt.
5. Sett `Main file path` til:

```text
app.py
```

6. Trykk Deploy.

## Viktige filer

```text
app.py                  # Selve appen
requirements.txt        # Python-pakker Streamlit installerer
oslo_universe.csv       # Bred Oslo Børs-liste
watchlist.csv           # Standard watchlist
portfolio.csv           # Porteføljeeksempel / tom portefølje
earnings_calendar.csv   # Enkel earnings-liste
insider_watch.csv       # Enkel insider-watchliste
notes.csv               # Notater
.streamlit/config.toml  # Standard dark mode/theme
```

## Deling på mobil

Når appen er deployet:

1. Åpne Streamlit-lenken på Android/iPhone.
2. I Chrome/Safari: velg «Legg til på startskjerm».
3. Da fungerer den nesten som en app.

## Viktig disclaimer

Dette er ikke personlig finansiell rådgivning. Verktøyet er kun laget for analyse, læring og screening. Gratis datakilder kan ha feil, forsinkelser eller manglende tickere.
