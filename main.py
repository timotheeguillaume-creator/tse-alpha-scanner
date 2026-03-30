import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

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
        # On télécharge 5 jours pour être sûr d'avoir de la donnée
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if df.empty or len(df) < 2:
            return 0.0
        
        # Extraction sécurisée (gère le format Multi-Index de yfinance)
        close_col = df['Close']
        c1 = float(close_col.iloc[-1].values[0]) if hasattr(close_col.iloc[-1], 'values') else float(close_col.iloc[-1])
        c2 = float(close_col.iloc[-2].values[0]) if hasattr(close_col.iloc[-2], 'values') else float(close_col.iloc[-2])
        
        return ((c1 - c2) / c2) * 100
    except Exception as e:
        print(f"Erreur sur {ticker}: {e}")
        return 0.0

def run_analysis():
    ndq = get_perf("^IXIC")
    jpy = get_perf("JPY=X")
    rates = get_perf("^TNX")
    
    results = []
    for s in sectors:
        ndq_impact = ndq * s['exp_sens'] * 5
        yen_impact_val = jpy * s['exp_sens'] * 15
        rate_impact = (rates * s.get('rate_sens', 0) * 10)
        
        prob = 50.0 + ndq_impact + yen_impact_val + rate_impact
        prob = max(10.0, min(90.0, prob)) 
        
        results.append({
            "Secteur": s['name'],
            "Codes": s['range'],
            "ID": s['id'],
            "Prob. Hausse": f"{prob:.1f}%",
            "Impact Yen": "🔥 Positif" if yen_impact_val > 0.3 else "❄️ Négatif" if yen_impact_val < -0.3 else "➖ Neutre",
            "Biais": "🟢 LONG" if prob > 55 else "🔴 SHORT" if prob < 45 else "🟡 NEUTRE"
        })
    
    return pd.DataFrame(results).sort_values(by="Prob. Hausse", ascending=False)

# --- GÉNÉRATION HTML ---
df = run_analysis()
tokyo_tz = pytz.timezone('Asia/Tokyo')
now = datetime.now(tokyo_tz).strftime('%Y-%m-%d %H:%M:%S')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="60"> <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0d1117; color: #c9d1d9; padding: 30px; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
        .container {{ max-width: 1000px; }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        .status-bar {{ background: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 6px; margin-bottom: 20px; color: #8b949e; }}
        .table {{ border-color: #30363d; }}
        .table-dark {{ background-color: #0d1117; }}
        .badge-long {{ background-color: #238636; color: white; }}
        .badge-short {{ background-color: #da3633; color: white; }}
        .badge-neutral {{ background-color: #6e7681; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🇯🇵 TSE Alpha Scanner</h1>
        <div class="status-bar">
            🟢 <b>LIVE STATUS :</b> Mis à jour à <b>{now}</b> (Tokyo Time)
        </div>
        <div class="table-responsive">
            {df.to_html(classes='table table-dark table-hover', index=False, border=0)}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
