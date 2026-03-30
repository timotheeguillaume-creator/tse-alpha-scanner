import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# --- CONFIGURATION DES SECTEURS (Ta liste exacte + Mapping ADR/Drivers) ---
sectors = [
    {"id": "T17FD",  "name": "Foods", "range": "13xx - 14xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17ER",  "name": "Energy Resources", "range": "16xx / 50xx-53xx", "exp_sens": 0.2, "comm": "CL=F", "comm_name": "Oil"},
    {"id": "T17CM",  "name": "Construction", "range": "17xx - 19xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17CWT", "name": "Commercial/Wholesale", "range": "20xx - 34xx / 80xx", "exp_sens": 0.5, "adr": "8058.T", "adr_name": "Mitsubishi"},
    {"id": "T17RMC", "name": "Raw Mat. & Chemicals", "range": "35xx - 44xx", "exp_sens": 0.4, "adr": None},
    {"id": "T17PHR", "name": "Pharmaceutical", "range": "45xx", "exp_sens": 0.1, "adr": "TAK", "adr_name": "Takeda"},
    {"id": "T17SNM", "name": "Steel & Non-ferrous", "range": "54xx - 59xx", "exp_sens": 0.4, "comm": "HG=F", "comm_name": "Copper"},
    {"id": "T17M",   "name": "Machinery", "range": "60xx - 64xx", "exp_sens": 0.6, "adr": None},
    {"id": "T17EAPI", "name": "Electric & Precision", "range": "65xx - 71xx", "exp_sens": 0.9, "adr": "SONY", "adr_name": "Sony"},
    {"id": "T17ATE", "name": "Auto & Transport", "range": "72xx", "exp_sens": 0.8, "adr": "TM", "adr_name": "Toyota"},
    {"id": "T17RT",  "name": "Retail Trade", "range": "82xx", "exp_sens": -0.2, "adr": None},
    {"id": "T17B",   "name": "Banks", "range": "83xx - 84xx", "exp_sens": 0.0, "rate_sens": 0.9, "adr": "MUFG", "adr_name": "MUFG Bank"},
    {"id": "T17FIN", "name": "Financials", "range": "85xx - 87xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17RE",  "name": "Real Estate", "range": "88xx - 89xx", "exp_sens": -0.3, "adr": None},
    {"id": "T17TL",  "name": "Transp. & Logistics", "range": "90xx - 93xx", "exp_sens": 0.2, "adr": None},
    {"id": "T17EPG", "name": "Electric Power & Gas", "range": "95xx", "exp_sens": -0.5, "comm": "CL=F", "comm_name": "Oil (Inv.)"},
    {"id": "T17ISO", "name": "IT & Services", "range": "94xx / 96xx+", "exp_sens": 0.7, "adr": "NTTYY", "adr_name": "NTT"}
]

def get_perf(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if df.empty or len(df) < 2: return 0.0
        close_col = df['Close']
        c1 = float(close_col.iloc[-1].values[0]) if hasattr(close_col.iloc[-1], 'values') else float(close_col.iloc[-1])
        c2 = float(close_col.iloc[-2].values[0]) if hasattr(close_col.iloc[-2], 'values') else float(close_col.iloc[-2])
        return ((c1 - c2) / c2) * 100
    except: return 0.0

def run_analysis():
    # Données Macro
    ndq = get_perf("^IXIC")
    jpy = get_perf("JPY=X")
    rates = get_perf("^TNX")
    vix = get_perf("^VIX")
    fut = get_perf("NIY=F") # Nikkei Futures
    oil = get_perf("CL=F")
    copper = get_perf("HG=F")

    results = []
    for s in sectors:
        # Calcul Probabilité (Logic Genius sans le poids négatif du VIX)
        prob = 50.0
        prob += (ndq * s['exp_sens'] * 5)      # Impact Nasdaq
        prob += (jpy * s['exp_sens'] * 15)     # Impact Yen
        prob += (fut * 10)                     # Pression Futures Nikkei
        
        if 'rate_sens' in s:
            prob += (rates * s['rate_sens'] * 10)
        
        # Impact spécifique ADR ou Comm
        driver_label = "Macro"
        if s.get("adr"):
            adr_p = get_perf(s["adr"])
            prob += (adr_p * 15)
            driver_label = s["adr_name"]
        elif s.get("comm"):
            c_p = oil if s["comm"] == "CL=F" else copper
            prob += (c_p * s["exp_sens"] * 10)
            driver_label = s["comm_name"]

        prob = max(10.0, min(90.0, prob)) # Clamp sécurisé

        results.append({
            "Secteur": s['name'],
            "Codes": s['range'],
            "ID": s['id'],
            "Prob. Hausse": prob, # On garde en float pour le tri
            "Driver": driver_label,
            "Impact Yen": "🔥 Positif" if (jpy * s['exp_sens']) > 0.2 else "❄️ Négatif" if (jpy * s['exp_sens']) < -0.2 else "➖ Neutre",
            "Biais": "🟢 LONG" if prob > 55 else "🔴 SHORT" if prob < 45 else "🟡 NEUTRE"
        })
    
    # Tri par probabilité décroissante
    df = pd.DataFrame(results).sort_values(by="Prob. Hausse", ascending=False)
    
    # Formatage de la probabilité en string pour l'affichage après le tri
    df["Prob. Hausse"] = df["Prob. Hausse"].apply(lambda x: f"{x:.1f}%")
    
    return df, vix, fut, jpy

# --- GÉNÉRATION HTML ---
df_final, vix_val, fut_val, jpy_val = run_analysis()
tokyo_tz = pytz.timezone('Asia/Tokyo')
now = datetime.now(tokyo_tz).strftime('%Y-%m-%d %H:%M:%S')

# Sentiment Global
vix_status = "⚠️ PANIC HIGH" if vix_val > 5 else "✅ STABLE"
mkt_status = "🚀 BULLISH" if fut_val > 0.5 else "🩸 BEARISH" if fut_val < -0.5 else "➖ NEUTRAL"

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta http-equiv="refresh" content="60">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0d1117; color: #c9d1d9; padding: 20px; font-family: -apple-system,sans-serif; }}
        .container {{ max-width: 1100px; }}
        h1 {{ color: #58a6ff; font-weight: bold; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        .status-bar {{ background: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .card-stat {{ background: #1c2128; border: 1px solid #444c56; padding: 10px; border-radius: 6px; text-align: center; }}
        .label-stat {{ font-size: 0.8em; color: #8b949e; text-transform: uppercase; }}
        .val-stat {{ font-weight: bold; font-size: 1.1em; color: #58a6ff; }}
        .table {{ border-color: #30363d; color: #c9d1d9; }}
        .table-dark {{ background-color: #0d1117; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🇯🇵 TSE Alpha Sniper Dashboard</h1>
        
        <div class="status-bar row g-2">
            <div class="col-md-3"><div class="card-stat"><div class="label-stat">VIX Sentiment</div><div class="val-stat">{vix_status}</div></div></div>
            <div class="col-md-3"><div class="card-stat"><div class="label-stat">Mkt Pressure</div><div class="val-stat">{mkt_status}</div></div></div>
            <div class="col-md-3"><div class="card-stat"><div class="label-stat">Carry Trade</div><div class="val-stat">{"🔥 ACTIVE" if abs(jpy_val) > 0.3 else "❄️ CALM"}</div></div></div>
            <div class="col-md-3"><div class="card-stat"><div class="label-stat">Live Status (Seconds)</div><div class="val-stat">{now}</div></div></div>
        </div>

        <div class="table-responsive">
            {df_final.to_html(classes='table table-dark table-hover', index=False, border=0)}
        </div>
        
        <p class="mt-3 small text-muted">
            <b>Note:</b> Le score Prob. Hausse combine l'arbitrage ADR (Sony, Toyota, etc.), les Futures Nikkei et l'impact monétaire.
        </p>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
