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
