# InvestAI v8 Decision Intelligence

Nytt i v8:
- Decision Intelligence Engine
- Explain Score
- Bull/Base/Bear scenarioer
- Risk/Reward-estimater
- Conviction labels
- Thesis engine
- Top Ideas Engine
- Defensive / Rocket / Risk-Reward lister
- Bedre beslutningsstøtte fremfor bare visualisering

Start:
streamlit run app.py


## v8.1 Hotfix Flat

Denne versjonen fikser NameError for `scenario_estimates`, `conviction_label` og `build_thesis`.
Datafilene ligger flatt sammen med `app.py` for enklere GitHub/Streamlit-deploy.

Start lokalt:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```


## v8.6 Oslo Børs Universe
Denne versjonen inkluderer `oslo_universe.csv` og `watchlist.csv` med en bred liste over Oslo Børs / Oslo-relaterte tickere. Appen merger automatisk `watchlist.csv` med `oslo_universe.csv`, slik at du kan beholde egne aksjer og samtidig screene bredt. Gratisdata via yfinance kan mangle enkelte tickere, så ugyldige/manglende tickere hoppes over med advarsel i appen.
