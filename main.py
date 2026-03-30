import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import urllib.request
import xml.etree.ElementTree as ET

# --- CONFIGURATION DES SECTEURS ---
sectors = [
    {"id": "T17FD",  "name": "Foods", "range": "13xx - 14xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17ER",  "name": "Energy Resources", "range": "16xx / 50xx-53xx", "exp_sens": 0.05, "comm": "CL=F", "comm_name": "Oil"},
    {"id": "T17CM",  "name": "Construction", "range": "17xx - 19xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17CWT", "name": "Commercial/Wholesale", "range": "20xx - 34xx / 80xx", "exp_sens": 0.5, "adr": "8058.T", "adr_name": "Mitsubishi"},
    {"id": "T17RMC", "name": "Raw Mat. & Chemicals", "range": "35xx - 44xx", "exp_sens": 0.4, "adr": None},
    {"id": "T17PHR", "name": "Pharmaceutical", "range": "45xx", "exp_sens": 0.1, "adr": "TAK", "adr_name": "Takeda"},
    {"id": "T17SNM", "name": "Steel & Non-ferrous", "range": "54xx - 59xx", "exp_sens": 0.3, "comm": "HG=F", "comm_name": "Copper"},
    {"id": "T17M",   "name": "Machinery", "range": "60xx - 64xx", "exp_sens": 0.6, "adr": None},
    {"id": "T17EAPI", "name": "Electric & Precision", "range": "65xx - 71xx", "exp_sens": 0.9, "adr": "SONY", "adr_name": "Sony"},
    {"id": "T17ATE", "name": "Auto & Transport", "range": "72xx", "exp_sens": 0.8, "adr": "TM", "adr_name": "Toyota"},
    {"id": "T17RT",  "name": "Retail Trade", "range": "82xx", "exp_sens": -0.2, "adr": None},
    {"id": "T17B",   "name": "Banks", "range": "83xx - 84xx", "exp_sens": 0.0, "rate_sens": 1.2, "adr": "MUFG", "adr_name": "MUFG Bank"},
    {"id": "T17FIN", "name": "Financials", "range": "85xx - 87xx", "exp_sens": 0.1, "adr": None},
    {"id": "T17RE",  "name": "Real Estate", "range": "88xx - 89xx", "exp_sens": -0.3, "adr": None},
    {"id": "T17TL",  "name": "Transp. & Logistics", "range": "90xx - 93xx", "exp_sens": 0.2, "adr": None},
    {"id": "T17EPG", "name": "Electric Power & Gas", "range": "95xx", "exp_sens": -0.4, "comm": "CL=F", "comm_name": "Oil (Inv.)", "is_inverse": True, "is_safe_haven": True},
    {"id": "T17ISO", "name": "IT & Services", "range": "94xx / 96xx+", "exp_sens": 0.7, "adr": "NTTYY", "adr_name": "NTT"}
]

def get_news_intel():
    """Scanne les news japonaises pour les catalyseurs Alpha."""
    try:
        url = "https://news.google.com/rss/search?q=Nikkei+BoJ+Nuclear+Yen+intervention&hl=en-US&gl=US&ceid=US:en"
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')[:10]
        
        intel = {"intervention": False, "nuclear": False, "boj_hike": False, "latest_titles": []}
        for item in items:
            title = item.find('title').text.upper()
            intel["latest_titles"].append(title)
            if any(x in title for x in ["INTERVENTION", "MOF", "CURRENCY WATCH"]): intel["intervention"] = True
            if any(x in title for x in ["NUCLEAR", "RESTART", "TEPCO"]): intel["nuclear"] = True
            if any(x in title for x in ["BOJ", "RATE HIKE", "UEDA"]): intel["boj_hike"] = True
        return intel
    except:
        return {"intervention": False, "nuclear": False, "boj_hike": False, "latest_titles": []}

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
    ndq, jpy, rates = get_perf("^IXIC"), get_perf("JPY=X"), get_perf("^TNX")
    vix, fut, oil, copper = get_perf("^VIX"), get_perf("NIY=F"), get_perf("CL=F"), get_perf("HG=F")
    news = get_news_intel()

    results = []
    for s in sectors:
        prob = 50.0
        prob += (ndq * s['exp_sens'] * 4) + (fut * 12) + (jpy * s['exp_sens'] * 18)
        
        if 'rate_sens' in s:
            prob += (rates * s['rate_sens'] * 15)
            if news["boj_hike"]: prob += 10 # Boost Banques si News BoJ

        driver_label = "Macro"
        if s.get("adr"):
            prob += (get_perf(s["adr"]) * 20)
            driver_label = s["adr_name"]
        elif s.get("comm"):
            c_p = oil if s["comm"] == "CL=F" else copper
            if s.get("is_inverse"):
                # --- LOGIQUE SAFE HAVEN + NEWS ---
                panic_buffer = 0.5 if vix > 0 else 1.0
                prob -= (c_p * 25 * panic_buffer)
                if fut < -0.6: prob += 15 
                if news["nuclear"]: prob += 20 # Catalyst majeur
            else:
                prob += (c_p * 25)
            driver_label = s["comm_name"]

        if news["intervention"] and s["exp_sens"] > 0.5: prob -= 15 # Malus exportateurs

        prob = max(5.0, min(95.0, prob))
        results.append({"Secteur": s['name'], "Codes": s['range'], "ID": s['id'], "Score": prob, 
                        "Prob. Hausse": f"{prob:.1f}%", "Driver": driver_label, 
                        "Impact Yen": "🔥 Positif" if (jpy * s['exp_sens']) > 0.15 else "❄️ Négatif" if (jpy * s['exp_sens']) < -0.15 else "➖ Neutre",
                        "Biais": "🟢 LONG" if prob > 55 else "🔴 SHORT" if prob < 45 else "🟡 NEUTRE"})
    
    df = pd.DataFrame(results).sort_values(by="Score", ascending=False).drop(columns=['Score'])
    return df, vix, fut, jpy, news

# --- GÉNÉRATION HTML ---
df_final, vix_val, fut_val, jpy_val, news = run_analysis()
tokyo_tz = pytz.timezone('Asia/Tokyo')
now = datetime.now(tokyo_tz).strftime('%Y-%m-%d %H:%M:%S')

# Badges News
news_html = ""
if news["intervention"]: news_html += '<span class="badge bg-danger me-2">🚨 YEN INTERVENTION RISK</span>'
if news["nuclear"]: news_html += '<span class="badge bg-warning text-dark me-2">☢️ NUCLEAR RESTART NEWS</span>'
if news["boj_hike"]: news_html += '<span class="badge bg-primary me-2">🏦 BOJ HAWKISH BIAS</span>'
if not news_html: news_html = '<span class="text-muted">No major Alpha News detected.</span>'

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
        .status-bar {{ background: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; margin-bottom: 10px; }}
        .news-bar {{ background: #1c2128; border: 1px solid #444c56; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #58a6ff; }}
        .card-stat {{ background: #1c2128; border: 1px solid #444c56; padding: 10px; border-radius: 6px; text-align: center; }}
        .val-stat {{ font-weight: bold; font-size: 1.1em; color: #58a6ff; }}
        .table {{ border-color: #30363d; color: #c9d1d9; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🇯🇵 TSE Alpha Sniper Dashboard</h1>
        
        <div class="status-bar row g-2">
            <div class="col-md-3"><div class="card-stat">VIX<br><span class="val-stat">{"⚠️ PANIC" if vix_val > 5 else "✅ STABLE"}</span></div></div>
            <div class="col-md-3"><div class="card-stat">MKT PRESSURE<br><span class="val-stat">{"🩸 BEARISH" if fut_val < -0.4 else "🚀 BULLISH" if fut_val > 0.4 else "➖ NEUTRAL"}</span></div></div>
            <div class="col-md-3"><div class="card-stat">CARRY TRADE<br><span class="val-stat">{"🔥 ACTIVE" if abs(jpy_val) > 0.3 else "❄️ CALM"}</span></div></div>
            <div class="col-md-3"><div class="card-stat">TOKYO TIME<br><span class="val-stat">{now}</span></div></div>
        </div>

        <div class="news-bar">
            <small class="text-muted d-block mb-1">MARKET INTELLIGENCE FEED :</small>
            {news_html}
        </div>

        <div class="table-responsive">
            {df_final.to_html(classes='table table-dark table-hover', index=False, border=0)}
        </div>
        
        <p class="mt-3 small text-muted"><b>Logic Engine :</b> Intégration News RSS (Nucléaire/Yen) + Stratégie Valeur Refuge sur 95xx.</p>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
