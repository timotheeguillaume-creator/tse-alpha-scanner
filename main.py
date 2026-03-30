import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# --- MAPPING SECTEURS & ADRs (Le lien entre NY et Tokyo) ---
sectors = [
    {"id": "T17EAPI", "name": "Electric & Precision", "range": "65xx-71xx", "adr": "SONY", "exp": 0.9},
    {"id": "T17ATE", "name": "Auto & Transport", "range": "72xx", "adr": "TM", "exp": 0.8},
    {"id": "T17B", "name": "Banks", "range": "83xx-84xx", "adr": "MUFG", "rate_sens": 0.9},
    {"id": "T17ISO", "name": "IT & Services", "range": "94xx/96xx+", "adr": "NTTYY", "exp": 0.7},
    {"id": "T17CWT", "name": "Commercial/Wholesale", "range": "20xx-34xx", "adr": "8058.T", "exp": 0.5}, # Mitsubishi Corp
    {"id": "T17SNM", "name": "Steel & Non-ferrous", "range": "54xx-59xx", "comm": "HG=F", "exp": 0.4}, # Copper
    {"id": "T17ER", "name": "Energy Resources", "range": "16xx/50xx", "comm": "CL=F", "exp": 0.3}, # Oil
    {"id": "T17EPG", "name": "Electric Power & Gas", "range": "95xx", "comm": "CL=F", "exp": -0.5}, # Inverse Oil
    {"id": "T17PHR", "name": "Pharmaceutical", "range": "45xx", "adr": "TAK", "exp": 0.1},
    {"id": "T17RT", "name": "Retail Trade", "range": "82xx", "exp": -0.2},
    {"id": "T17RE", "name": "Real Estate", "range": "88xx-89xx", "exp": -0.3},
    {"id": "T17FD", "name": "Foods", "range": "13xx-14xx", "exp": 0.1}
]

def get_data(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if df.empty or len(df) < 2: return 0.0
        close_col = df['Close']
        c1 = float(close_col.iloc[-1].values[0]) if hasattr(close_col.iloc[-1], 'values') else float(close_col.iloc[-1])
        c2 = float(close_col.iloc[-2].values[0]) if hasattr(close_col.iloc[-2], 'values') else float(close_col.iloc[-2])
        return ((c1 - c2) / c2) * 100
    except: return 0.0

def run_analysis():
    # 1. Macro Drivers
    ndq = get_data("^IXIC")
    jpy = get_data("JPY=X")
    vix = get_data("^VIX")
    futures = get_data("NIY=F") # Nikkei 225 Futures
    oil = get_data("CL=F")
    copper = get_data("HG=F")
    
    # Global Sentiment Logic
    vix_panic = "⚠️ HIGH" if vix > 5 else "✅ LOW"
    market_pressure = "🚀 BULLISH" if futures > 0.5 else "🩸 BEARISH" if futures < -0.5 else "➖ NEUTRAL"
    
    results = []
    for s in sectors:
        # Base Probability
        prob = 50.0
        
        # Factor 1: Index & Futures (Poids 30%)
        prob += (ndq * 0.1) + (futures * 10)
        
        # Factor 2: ADR Arbitrage (Poids 40%) - Le plus précis
        if "adr" in s:
            adr_perf = get_data(s["adr"])
            prob += (adr_perf * 15)
            
        # Factor 3: Commodities (Poids 20%)
        if s.get("comm") == "CL=F": prob += (oil * s["exp"] * 10)
        if s.get("comm") == "HG=F": prob += (copper * 10)
        
        # Factor 4: JPY Velocity & VIX (Poids 10%)
        prob += (jpy * s.get("exp", 0) * 10)
        if vix > 10: prob -= 15 # Peine de panique
        
        prob = max(5.0, min(95.0, prob))
        
        results.append({
            "Secteur": s['name'],
            "Codes": s['range'],
            "Prob. Hausse": f"{prob:.1f}%",
            "Driver": s.get("adr", s.get("comm", "Macro")),
            "Biais": "🟢 LONG" if prob > 58 else "🔴 SHORT" if prob < 42 else "🟡 NEUTRAL"
        })

    return pd.DataFrame(results).sort_values(by="Prob. Hausse", ascending=False), vix_panic, market_pressure, jpy

# --- GÉNÉRATION HTML ---
df, vix_p, mkt_p, jpy_v = run_analysis()
tokyo_tz = pytz.timezone('Asia/Tokyo')
now = datetime.now(tokyo_tz).strftime('%Y-%m-%d %H:%M:%S')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta http-equiv="refresh" content="60">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0d1117; color: #c9d1d9; padding: 20px; font-family: sans-serif; }}
        .card {{ background: #161b22; border: 1px solid #30363d; margin-bottom: 15px; padding: 15px; border-radius: 8px; }}
        .val {{ font-weight: bold; color: #58a6ff; }}
        .table {{ color: #c9d1d9; border-color: #30363d; }}
        .LONG {{ color: #3fb950; font-weight: bold; }}
        .SHORT {{ color: #f85149; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">🇯🇵 TSE Alpha Sniper Dashboard</h1>
        
        <div class="row">
            <div class="col-md-3"><div class="card">VIX PANIC<br><span class="val">{vix_p}</span></div></div>
            <div class="col-md-3"><div class="card">MKT PRESSURE<br><span class="val">{mkt_p}</span></div></div>
            <div class="col-md-3"><div class="card">CARRY TRADE HEAT<br><span class="val">{"🔥 HIGH" if abs(jpy_v) > 0.4 else "❄️ LOW"}</span></div></div>
            <div class="col-md-3"><div class="card">LAST UPDATE<br><span class="val">{now}</span></div></div>
        </div>

        <div class="table-responsive card">
            {df.to_html(classes='table table-dark table-hover', index=False, border=0)}
        </div>
        
        <div class="mt-3 small text-muted">
            <b>Note:</b> L'arbitrage ADR (Toyota, Sony, MUFG) est le driver principal du score. 
            Si le VIX est en hausse, les probabilités sont automatiquement dégradées.
        </div>
    </div>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html)
