import yfinance as yf
import pandas as pd
from datetime import datetime

# --- CONFIGURATION DES SECTEURS ---
sectors = [
    {"id": "T17FD",  "name": "Foods", "range": "13xx - 14xx", "exp_sens": 0.1},
    {"id": "T17ER",  "name": "Energy Resources", "range": "16xx / 50xx-53xx", "exp_sens": 0.2},
    {"id": "T17CM",  "name": "Construction", "range": "17xx - 19xx", "exp_sens": 0.1},
    {"id": "T17CWT", "name": "Commercial/Wholesale", "range": "20xx - 34xx / 80xx", "exp_sens": 0.5},
    {"id": "T17RMC", "name": "Raw Mat. & Chemicals", "range": "35xx - 44xx", "exp_sens": 0.4},
    {"id": "T17PHR", "name": "Pharmaceutical", "range": "45xx", "exp_sens": 0.1},
    {"id": "T17SNM", "name": "Steel & Non-ferrous", "range": "54xx - 59xx", "exp_sens": 0.4},
    {"id": "T17M",   "name": "Machinery", "range": "60xx - 64xx", "exp_sens": 0.6},
    {"id": "T17EAPI", "name": "Electric & Precision", "range": "65xx - 71xx", "exp_sens": 0.9},
    {"id": "T17ATE", "name": "Auto & Transport", "range": "72xx", "exp_sens": 0.8},
    {"id": "T17RT",  "name": "Retail Trade", "range": "82xx", "exp_sens": -0.2},
    {"id": "T17B",   "name": "Banks", "range": "83xx - 84xx", "exp_sens": 0.0, "rate_sens": 0.9},
    {"id": "T17FIN", "name": "Financials", "range": "85xx - 87xx", "exp_sens": 0.1},
    {"id": "T17RE",  "name": "Real Estate", "range": "88xx - 89xx", "exp_sens": -0.3},
    {"id": "T17TL",  "name": "Transp. & Logistics", "range": "90xx - 93xx", "exp_sens": 0.2},
    {"id": "T17EPG", "name": "Electric Power & Gas", "range": "95xx", "exp_sens": -0.5},
    {"id": "T17ISO", "name": "IT & Services", "range": "94xx / 96xx+", "exp_sens": 0.7}
]

def get_perf(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if len(df) < 2: return 0.0
        # On prend les deux dernières clôtures valides
        c1 = df['Close'].iloc[-1].item()
        c2 = df['Close'].iloc[-2].item()
        return ((c1 - c2) / c2) * 100
    except:
        return 0.0

def run_analysis():
    # Récupération individuelle pour éviter qu'une erreur bloque tout
    ndq = get_perf("^IXIC")
    jpy = get_perf("JPY=X")
    rates = get_perf("^TNX") # Ici c'est la variation du rendement 10 ans US
    
    results = []
    for s in sectors:
        # 1. Calcul de l'influence Nasdaq (Beta de secteur)
        ndq_impact = ndq * s['exp_sens'] * 5
        
        # 2. Calcul de l'impact Yen (USDJPY up = Yen faible = Bon pour export)
        # On multiplie par 15 pour donner du poids au change
        yen_impact_val = jpy * s['exp_sens'] * 15
        
        # 3. Calcul de l'impact Taux (Uniquement pour les banques)
        rate_impact = (rates * s.get('rate_sens', 0) * 10)
        
        # Score final
        prob = 50.0 + ndq_impact + yen_impact_val + rate_impact
        prob = max(10, min(90, prob)) # Clamp plus réaliste entre 10% et 90%
        
        results.append({
            "Secteur": s['name'],
            "Codes": s['range'],
            "Prob. Hausse": f"{prob:.1f}%",
            "Impact Yen": "🔥 Positif" if yen_impact_val > 0.5 else "❄️ Négatif" if yen_impact_val < -0.5 else "➖ Neutre",
            "Biais": "🟢 LONG" if prob > 55 else "🔴 SHORT" if prob < 45 else "🟡 NEUTRE"
        })
    
    return pd.DataFrame(results).sort_values(by="Prob. Hausse", ascending=False)

# Génération HTML
df = run_analysis()
now = datetime.now().strftime('%Y-%m-%d %H:%M')
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0e1117; color: #ffffff; padding: 20px; }}
        .table {{ border-color: #333; color: white; }}
        h1 {{ color: #58a6ff; }}
    </style>
</head>
<body>
    <h1>🇯🇵 TSE Morning Alpha Scanner</h1>
    <p>Dernière mise à jour : {now} (Tokyo Time)</p>
    <div class="table-responsive">
        {df.to_html(classes='table table-dark table-striped', index=False)}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
