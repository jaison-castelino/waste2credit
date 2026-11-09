"""Waste to Credit Studio: small POC of the waste management and credit allocation service.
Run:  pip install -r requirements.txt  &&  streamlit run app.py
All names, numbers and factors are demo placeholders."""
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Waste to Credit Studio", page_icon="♻️", layout="wide")
COL = {"PET": "#38BDF8", "HDPE": "#A78BFA", "Dry": "#34D399", "ok": "#34D399", "warn": "#FBBF24", "fail": "#FB7185", "idle": "#475569"}
STATUS = {"Checked": "#94A3B8", "Under review": "#FBBF24", "Returned": "#FB923C", "Rejected": "#FB7185",
          "Posted": "#38BDF8", "Verified": "#A78BFA", "Retired": "#34D399"}
st.markdown("""<style>
.stApp{background:radial-gradient(1100px 600px at 8% -10%,#1e1b4b 0%,#0b1020 55%)}
.hero{font-size:2.3rem;font-weight:800;background:linear-gradient(90deg,#38BDF8,#A78BFA,#34D399);-webkit-background-clip:text;color:transparent;line-height:1.1}
.sub{color:#9CA3AF;margin:.2rem 0 .8rem}
.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:16px;padding:12px 16px;margin-bottom:8px}
.card span{color:#9CA3AF;font-size:.7rem;text-transform:uppercase;letter-spacing:.09em;display:block}
.card b{font-size:1.7rem}
.chip{display:inline-block;padding:6px 13px;border-radius:999px;font-weight:700;margin:0 6px 8px 0;font-size:.8rem;color:#0b1020}
</style>""", unsafe_allow_html=True)

CLIENTS = {
    "Acme Foods": dict(target=3000, rewards=True, scale=1.0,
                       sites={"Plant A": (12.99, 77.55), "Plant B": (12.93, 77.62), "HQ": (12.97, 77.59)},
                       partners=["GreenLoop Recyclers", "EcoCycle"]),
    "Nova Retail": dict(target=1800, rewards=False, scale=0.6,
                        sites={"Store Hub": (13.02, 77.65), "Warehouse": (12.90, 77.50)},
                        partners=["ReNew Hub", "CleanChain"]),
}
ROLES = {
    "Data Collection Team": ("You collect waste data from client sites and partners.", ["Log a collection", "Site map"]),
    "Platform Admin": ("You check batches, clear flags and post credits.", ["Overview", "Review queue", "Post credits", "Batch trail", "Site map"]),
    "Verifier": ("You check the records and sign off the credits.", ["Verify credits", "Batch trail"]),
    "Client ESG Manager": ("You decide how credits are used against targets.", ["Overview", "Retire credits", "Insights"]),
    "Finance / Management": ("You use reports and budgets to make decisions.", ["Overview", "Insights"]),
}
def card(label, value, color="#E5E7EB"):
    return f'<div class="card"><span>{label}</span><b style="color:{color}">{value}</b></div>'
def chip(text, state):
    return f'<span class="chip" style="background:{COL[state]}">{text}</span>'
def style(fig, h=300):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=h, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15))
    return fig
def now():
    return datetime.now().strftime("%d %b, %H:%M")

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### ♻️ Client")
    client = st.selectbox("Organisation", list(CLIENTS), label_visibility="collapsed")
    cfg = CLIENTS[client]
    st.caption(f"EPR target: {cfg['target']:,} credits | Rewards: {'on' if cfg['rewards'] else 'off'}")
    st.markdown("### 👤 You are")
    role = st.radio("Role", list(ROLES), label_visibility="collapsed")
    with st.expander("Conversion rules (placeholders)"):
        RULES = {}
        for k, (p, e, c) in {"PET": (10, 1.0, 1.5), "HDPE": (8, 1.0, 1.2), "Dry": (3, 0.0, 0.8)}.items():
            a, b, d = st.columns(3)
            RULES[k] = (a.number_input(f"{k} pts/kg", value=float(p), key=f"p{k}"),
                        b.number_input("EPR", value=e, key=f"e{k}"),
                        d.number_input("CO2e", value=c, key=f"c{k}"))

def convert(net):
    return dict(kg=round(sum(net.values()), 1), points=round(sum(net[k] * RULES[k][0] for k in net)),
                epr=round(sum(net[k] * RULES[k][1] for k in net), 1),
                tco2e=round(sum(net[k] * RULES[k][2] for k in net) / 1000, 3))

# ---------------- data ----------------
BASE = ["Collected by the Data Collection Team", "Entered into the platform", "G2 passed: batch is complete",
        "G3 passed: low risk", "G4 passed: credits calculated"]
AFTER = {"Posted": ["Posted by the Platform Admin (G5)"], "Verified": ["Posted by the Platform Admin (G5)", "Signed off by the Verifier (G6)"],
         "Retired": ["Posted by the Platform Admin (G5)", "Signed off by the Verifier (G6)", "Retired by the ESG Manager"]}
if "b" not in st.session_state:
    rng = np.random.default_rng(7)
    rows = []
    for cl, c in CLIENTS.items():
        for i in range(8):
            net = {"PET": rng.integers(60, 200), "HDPE": rng.integers(40, 140), "Dry": rng.integers(100, 300)}
            site = str(rng.choice(list(c["sites"])))
            la, lo = c["sites"][site]
            status = ["Retired", "Retired", "Verified", "Verified", "Posted", "Posted", "Checked", "Under review"][i]
            steps = BASE[:] if status != "Under review" else BASE[:2] + ["G2 passed: batch is complete", "G3 flagged: medium risk. Sent to Platform Admin"]
            steps += AFTER.get(status, [])
            rows.append(dict(client=cl, site=site, partner=str(rng.choice(c["partners"])), **convert(net),
                             cont=int(rng.integers(2, 12)), risk="Medium" if status == "Under review" else "Low",
                             flags="Weight is higher than usual" if status == "Under review" else "",
                             lat=la + rng.normal(0, .004), lon=lo + rng.normal(0, .004), status=status,
                             trail=[f"{2 + j:02d} Nov, 1{i % 6}:{10 + j * 7}|{s}" for j, s in enumerate(steps)]))
    st.session_state.b = pd.DataFrame(rows)
B = lambda: st.session_state.b
def cur():
    d = B()
    return d[d.client == client]
def move(i, status, text):
    B().at[i, "status"] = status
    B().at[i, "trail"].append(f"{now()}|{text}")
def flash(msg):
    st.session_state["flash"] = msg
    st.rerun()
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

# ---------------- pages ----------------
def page_log():
    L, R = st.columns([1, 1.4], gap="large")
    with L:
        site = st.selectbox("Client site", list(cfg["sites"]))
        partner = st.selectbox("Collection partner", cfg["partners"])
        pet = st.slider("PET (kg)", 0, 500, 120)
        hdpe = st.slider("HDPE (kg)", 0, 500, 80)
        dry = st.slider("Dry waste (kg)", 0, 500, 200)
        cont = st.slider("Contamination (%)", 0, 40, 5)
        up = st.file_uploader("Receipt photo", type=["png", "jpg", "jpeg", "pdf"])
        sample = st.checkbox("Use a sample receipt", True)
        with st.expander("Try a fraud case"):
            dup = st.toggle("Receipt already used", False)
            wrong = st.toggle("Collected away from the site", False)
    f = 1 - cont / 100
    net = {"PET": pet * f, "HDPE": hdpe * f, "Dry": dry * f}
    total = pet + hdpe + dry
    res = convert(net)
    flags, score = [], 0
    for cond, pts, msg in [(dup, 60, "Receipt was used before"), (total > 1000, 40, f"Weight is high: {total} kg vs about 400 kg usual"),
                           (wrong, 30, "Location does not match the site"), (cont > 15, 20, "Contamination is high")]:
        if cond:
            score += pts
            flags.append(msg)
    risk = "Low" if score < 20 else "Medium" if score < 50 else "High"
    g2 = (up is not None) or sample
    s2 = "ok" if g2 else "fail"
    s3 = "idle" if not g2 else {"Low": "ok", "Medium": "warn", "High": "fail"}[risk]
    with R:
        st.markdown(chip("G2 Complete", s2) + chip(f"G3 Fraud check: {risk}", s3) + chip("G4 Credits", "ok" if (g2 and risk == "Low") else "idle"), unsafe_allow_html=True)
        if not g2:
            st.error("Receipt is missing. The batch will go back to the Data Collection Team.")
        for fl in flags:
            st.warning(fl)
        c1, c2, c3 = st.columns(3)
        c1.markdown(card("Green points", f"{res['points']:,}", COL["Dry"]), unsafe_allow_html=True)
        c2.markdown(card("EPR credits", f"{res['epr']:,}", COL["PET"]), unsafe_allow_html=True)
        c3.markdown(card("tCO2e (est.)", res["tco2e"], COL["HDPE"]), unsafe_allow_html=True)
        sk = go.Figure(go.Sankey(
            node=dict(label=["PET", "HDPE", "Dry waste", "Green points", "EPR credits", "Carbon offset"], pad=16, thickness=14,
                      color=[COL["PET"], COL["HDPE"], COL["Dry"], "#FBBF24", "#38BDF8", "#A78BFA"]),
            link=dict(source=[0, 1, 2, 0, 1, 0, 1, 2], target=[3, 3, 3, 4, 4, 5, 5, 5],
                      value=[net["PET"], net["HDPE"], net["Dry"], net["PET"], net["HDPE"], net["PET"], net["HDPE"], net["Dry"]],
                      color=["rgba(148,163,184,.25)"] * 8)))
        st.plotly_chart(style(sk, 230), width="stretch")
        if st.button("Submit batch", type="primary", disabled=res["kg"] <= 0):
            la, lo = cfg["sites"][site]
            off = 0.06 if wrong else 0
            steps = ["Collected by the Data Collection Team", "Entered into the platform"]
            if not g2:
                status = "Returned"
                steps += ["G2 failed: receipt missing. Returned to the Data Collection Team"]
            elif risk == "Low":
                status = "Checked"
                steps += ["G2 passed: batch is complete", "G3 passed: low risk", "G4 passed: credits calculated"]
            else:
                status = "Under review"
                steps += ["G2 passed: batch is complete", f"G3 flagged: {risk.lower()} risk. Sent to Platform Admin"]
            row = dict(client=client, site=site, partner=partner, **res, cont=cont, risk=risk, flags="; ".join(flags),
                       lat=la + off, lon=lo + off, status=status, trail=[f"{now()}|{s}" for s in steps])
            st.session_state.b = pd.concat([B(), pd.DataFrame([row])], ignore_index=True)
            flash({"Returned": "Sent back: receipt missing", "Checked": "Batch passed all checks", "Under review": "Batch sent to the Platform Admin for review"}[status])

def page_map():
    d = cur()
    fig = go.Figure()
    sites = cfg["sites"]
    fig.add_trace(go.Scattermap(lat=[v[0] for v in sites.values()], lon=[v[1] for v in sites.values()], mode="markers+text",
                                text=list(sites), textposition="top right", marker=dict(size=22, color="#64748B"), name="Client sites"))
    for s, g in d.groupby("status"):
        fig.add_trace(go.Scattermap(lat=g.lat, lon=g.lon, mode="markers", marker=dict(size=11, color=STATUS[s]), name=s,
                                    text=g.site + " | " + g.kg.astype(str) + " kg"))
    fig.update_layout(map=dict(style="carto-darkmatter", center=dict(lat=np.mean([v[0] for v in sites.values()]), lon=np.mean([v[1] for v in sites.values()])), zoom=10.5))
    st.plotly_chart(style(fig, 460), width="stretch")
    st.caption("Grey circles are client sites. A dot far from its site means the location did not match.")

def page_overview():
    d = cur()
    ok = d[d.status.isin(["Posted", "Verified", "Retired"])]
    t = st.columns(5)
    items = [("Waste collected (kg)", f"{d[d.status != 'Rejected'].kg.sum():,.0f}", COL["Dry"]), ("Green points", f"{ok.points.sum():,}" if cfg["rewards"] else "Off", "#FBBF24"),
             ("EPR credits", f"{ok.epr.sum():,.0f}", COL["PET"]), ("tCO2e (est.)", f"{ok.tco2e.sum():.2f}", COL["HDPE"]),
             ("Batches with issues", int(d.status.isin(["Under review", "Returned", "Rejected"]).sum()), COL["fail"])]
    for c, (a, b, k) in zip(t, items):
        c.markdown(card(a, b, k), unsafe_allow_html=True)
    L, R = st.columns(2, gap="large")
    with L:
        retired = d.loc[d.status == "Retired", "epr"].sum()
        g = go.Figure(go.Indicator(mode="gauge+number", value=retired, title={"text": "EPR retired vs target"},
                                   gauge=dict(axis=dict(range=[0, cfg["target"]]), bar=dict(color=COL["PET"]), bgcolor="rgba(255,255,255,.06)", borderwidth=0)))
        st.plotly_chart(style(g, 270), width="stretch")
    with R:
        p = d[d.status != "Rejected"].groupby("partner", as_index=False).agg(kg=("kg", "sum"), clean=("cont", "mean"))
        fig = px.bar(p, x="partner", y="kg", color="clean", title="Partner performance (colour = contamination %)",
                     color_continuous_scale=["#34D399", "#FBBF24", "#FB7185"])
        st.plotly_chart(style(fig, 270), width="stretch")
    rep = d[d.status.isin(["Verified", "Retired"])][["site", "partner", "kg", "points", "epr", "tco2e", "status"]]
    st.download_button("⬇️ Download compliance report (verified credits)", rep.to_csv(index=False), "compliance_report.csv", "text/csv")

def page_queue():
    q = cur()[cur().status == "Under review"]
    if q.empty:
        st.success("Nothing to review right now.")
    for i, r in q.iterrows():
        with st.container(border=True):
            a, b, c = st.columns([2.2, 1, 1])
            a.markdown(f"**#{i} · {r.site}** · {r.partner} · {r.kg} kg  \n:orange[{r.risk} risk]: {r['flags'] or 'Needs a second look'}")
            if b.button("Clear flags", key=f"c{i}", width="stretch"):
                move(i, "Checked", "Platform Admin cleared the flags")
                flash(f"Batch #{i} cleared")
            if c.button("Reject", key=f"r{i}", width="stretch"):
                move(i, "Rejected", "Platform Admin rejected the batch")
                flash(f"Batch #{i} rejected")
    n = int((cur().status == "Returned").sum())
    if n:
        st.caption(f"{n} batch(es) were returned to the Data Collection Team for missing items.")

def page_post():
    q = cur()[cur().status == "Checked"]
    if q.empty:
        st.info("No checked batches are waiting to be posted.")
        return
    st.dataframe(q[["site", "partner", "kg", "points", "epr", "tco2e"]], width="stretch")
    if st.button("Approve and post all (G5)", type="primary"):
        for i in q.index:
            move(i, "Posted", "Posted by the Platform Admin (G5)")
        flash(f"{len(q)} batch(es) posted to the client ledger")

def page_verify():
    q = cur()[cur().status == "Posted"]
    if q.empty:
        st.info("No posted credits are waiting for sign-off.")
        return
    st.dataframe(q[["site", "partner", "kg", "epr", "tco2e", "cont"]].rename(columns={"cont": "contamination %"}), width="stretch")
    if st.button("Sign off these credits (G6)", type="primary"):
        for i in q.index:
            move(i, "Verified", "Signed off by the Verifier (G6)")
        flash(f"{len(q)} batch(es) verified")

def page_retire():
    d = cur()
    ver = d[d.status == "Verified"].sort_index()
    avail = int(ver.epr.sum())
    L, R = st.columns([1, 1.2], gap="large")
    with L:
        st.markdown(card("Verified EPR credits available", f"{avail:,}", COL["HDPE"]), unsafe_allow_html=True)
        if avail >= 1:
            amt = st.slider("EPR credits to retire", 0, avail, avail)
            if st.button("Retire against the EPR target", type="primary"):
                left = amt
                for i, r in ver.iterrows():
                    if r.epr <= left:
                        move(i, "Retired", "Retired by the ESG Manager")
                        left -= r.epr
                flash("Credits retired")
        else:
            st.info("Credits must be verified before they can be retired.")
        if cfg["rewards"]:
            st.markdown(card("Green points given to employees", f"{d[d.status.isin(['Posted', 'Verified', 'Retired'])].points.sum():,}", COL["Dry"]), unsafe_allow_html=True)
    with R:
        retired = d.loc[d.status == "Retired", "epr"].sum()
        g = go.Figure(go.Indicator(mode="gauge+number", value=retired, title={"text": "EPR retired vs target"},
                                   gauge=dict(axis=dict(range=[0, cfg["target"]]), bar=dict(color=COL["Dry"]), bgcolor="rgba(255,255,255,.06)", borderwidth=0)))
        st.plotly_chart(style(g, 300), width="stretch")

def page_trail():
    d = cur()
    i = st.selectbox("Choose a batch", d.index[::-1], format_func=lambda i: f"#{i} · {d.at[i, 'site']} · {d.at[i, 'kg']} kg · {d.at[i, 'status']}")
    r = d.loc[i]
    L, R = st.columns([1, 1.3], gap="large")
    with L:
        st.markdown(chip(r.status, "ok") .replace(COL["ok"], STATUS[r.status]), unsafe_allow_html=True)
        st.markdown(card("Green points", f"{r.points:,}", COL["Dry"]) + card("EPR credits", f"{r.epr:,}", COL["PET"]) + card("tCO2e (est.)", r.tco2e, COL["HDPE"]), unsafe_allow_html=True)
    with R:
        html = ""
        for s in r.trail:
            when, text = s.split("|")
            c = COL["fail"] if any(w in text.lower() for w in ["failed", "rejected"]) else COL["warn"] if any(w in text.lower() for w in ["flagged", "cleared"]) else COL["ok"]
            html += f'<div style="display:flex;gap:12px;margin-bottom:12px"><div style="width:12px;height:12px;border-radius:50%;background:{c};margin-top:5px;flex:none"></div><div><b>{text}</b><br><span style="color:#9CA3AF;font-size:.78rem">{when}</span></div></div>'
        st.markdown(html, unsafe_allow_html=True)

def page_insights():
    d = cur()
    rng = np.random.default_rng(3)
    i = np.arange(12)
    hist = 900 * cfg["scale"] * (1 + 0.02 * i) * (1 + 0.25 * np.sin(2 * np.pi * i / 12)) * rng.normal(1, 0.04, 12)
    slope, icpt = np.polyfit(i, hist, 1)
    season = hist / (slope * i + icpt)
    fi = np.arange(12, 15)
    fc = (slope * fi + icpt) * season[fi % 12]
    months = pd.period_range("2025-11", periods=15, freq="M").strftime("%b %y")
    fig = go.Figure()
    fig.add_scatter(x=months[:12], y=hist, name="Collected (kg)", line=dict(color=COL["Dry"], width=3))
    fig.add_scatter(x=months[11:], y=np.r_[hist[-1], fc], name="Forecast", line=dict(color=COL["HDPE"], width=3, dash="dash"))
    fig.add_scatter(x=months[12:], y=fc * 1.1, line=dict(width=0), showlegend=False)
    fig.add_scatter(x=months[12:], y=fc * 0.9, fill="tonexty", fillcolor="rgba(167,139,250,.2)", line=dict(width=0), name="Range")
    fig.update_layout(title="Waste collected and next 3 months")
    st.plotly_chart(style(fig, 300), width="stretch")
    y1, y2 = st.columns(2, gap="large")
    with y1:
        haircut = st.slider("Credits we may lose in audit (%)", 0, 30, 10)
        expected = fc.sum() * 0.55 * (1 - haircut / 100)
        have = d[d.status.isin(["Posted", "Verified", "Retired"])].epr.sum()
        gap = cfg["target"] - have - expected
        st.markdown(card("EPR credits expected (next 3 months)", f"{expected:,.0f}", COL["PET"]), unsafe_allow_html=True)
        st.markdown(card("Short of target by" if gap > 0 else "Ahead of target by", f"{abs(gap):,.0f}", COL["fail"] if gap > 0 else COL["ok"]), unsafe_allow_html=True)
    with y2:
        price = st.slider("Price per EPR credit (demo)", 10, 100, 40)
        sc = pd.DataFrame({"Scenario": ["Low", "Base", "High"], "m": [0.8, 1.0, 1.4]})
        sc["Cost to cover the gap"] = max(gap, 0) * price * sc.m
        st.plotly_chart(style(px.bar(sc, x="Scenario", y="Cost to cover the gap", color="Scenario",
                                     color_discrete_sequence=[COL["Dry"], COL["PET"], COL["fail"]]), 250), width="stretch")

PAGES = {"Log a collection": page_log, "Site map": page_map, "Overview": page_overview, "Review queue": page_queue,
         "Post credits": page_post, "Batch trail": page_trail, "Verify credits": page_verify,
         "Retire credits": page_retire, "Insights": page_insights}

# ---------------- main ----------------
st.markdown('<div class="hero">Waste to Credit Studio</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub">{client} · {role}: {ROLES[role][0]}</div>', unsafe_allow_html=True)
opts = ROLES[role][1]
page = st.segmented_control("Page", opts, default=opts[0], key=f"nav_{role}", label_visibility="collapsed") or opts[0]
PAGES[page]()