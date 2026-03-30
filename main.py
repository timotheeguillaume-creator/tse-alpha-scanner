import yfinance as yf
import pandas as pd
from datetime import datetime

# --- CONFIGURATION DES SECTEURS (Ta liste Pine Script) ---
sectors = [
    {"id": "T17FD",  "name": "Foods", "range": "13xx - 14xx", "exp_sens": 0.1},
    {"id": "T17ER",  "name": "Energy Resources", "range": "16xx / 50xx - 53xx", "exp_sens": 0.2},
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

def get_data():
    # Nasdaq, USD/JPY, US 10Y Yield
    tickers = ["^IXIC", "JPY=X", "^TNX"]
    data = yf.download(tickers, period="2d", interval="1d")
    
    ndq_pc = ((data['Close']['^IXIC'].iloc[-1] - data['Close']['^IXIC'].iloc[-2]) / data['Close']['^IXIC'].iloc[-2]) * 100
    jpy_pc = ((data['Close']['JPY=X'].iloc[-1] - data['Close']['JPY=X'].iloc[-2]) / data['Close']['JPY=X'].iloc[-2]) * 100
    rate_diff = data['Close']['^TNX'].iloc[-1] - data['Close']['^TNX'].iloc[-2]
    
    return ndq_pc, jpy_pc, rate_diff

def run_analysis():
    ndq, jpy, rates = get_data()
    results = []

    for s in sectors:
        # Calcul de l'impact Yen (USDJPY up = Yen faible = Positif pour exportateurs)
        yen_impact_score = jpy * s['exp_sens'] * 10
        
        # Probabilité de base influencée par le Nasdaq et les taux
        prob = 50.0 + (ndq * s['exp_sens'] * 5) + yen_impact_score
        if 'rate_sens' in s:
            prob += (rates * s['rate_sens'] * 50)
        
        prob = max(5, min(95, prob)) # Clamp entre 5% et 95%
        
        results.append({
            "Secteur": s['name'],
            "Codes": s['range'],
            "ID": s['id'],
            "Prob. Hausse": f"{prob:.1f}%",
            "Impact Yen": "🔥 Positif" if yen_impact_score > 2 else "❄️ Négatif" if yen_impact_score < -2 else "➖ Neutre",
            "Biais": "🟢 LONG" if prob > 60 else "🔴 SHORT" if prob < 40 else "🟡 NEUTRE"
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
    <title>Tokyo Alpha Scan</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0e1117; color: #ffffff; padding: 20px; font-family: sans-serif; }}
        .table {{ border-color: #333; }}
        .table-dark {{ background-color: #161b22; }}
        h1 {{ color: #58a6ff; font-weight: bold; }}
        .update-time {{ color: #8b949e; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>🇯🇵 TSE Morning Alpha Scanner</h1>
    <p class="update-time">Dernière mise à jour : {now} (Tokyo Time)</p>
    {df.to_html(classes='table table-dark table-striped', index=False)}
    <footer class="mt-4 text-muted">Analyse basée sur la clôture US et le taux de change JPY.</footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
