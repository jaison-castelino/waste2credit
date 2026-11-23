"""Waste to Credit Studio: small POC of the waste management and credit allocation service.
Run:  pip install -r requirements.txt  &&  streamlit run app.py
All names, numbers and factors are demo placeholders.

Follows the Functional Process and Workflow Specification, including:
  Module 2A  chain of custody and handover tracking (control gates C1 to C4, plastic / e-waste / organic streams)
  Module 2B  agricultural land and cultivated land tracking (parcels, practice log, farmer confirmation)
  Module 3   the waste-streams table (how each stream is counted and which credit it can earn)
  Module 4   append-only ledger journal, serial numbers on retirement, versioned and dated rule sets
  Feature 3  fraud checks: duplicate receipt, weight spike, capacity plausibility, geo-tag, time (via C2), category mix, partner pattern,
             self-dealing, parcel overlap, area against land record, practice against imagery and fertiliser purchases, bulk entry"""
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Waste to Credit Studio", page_icon="♻️", layout="wide")
COL = {"PET": "#38BDF8", "HDPE": "#A78BFA", "Dry": "#34D399", "ok": "#34D399", "warn": "#FBBF24", "fail": "#FB7185", "idle": "#475569"}
STATUS = {"Checked": "#94A3B8", "Under review": "#FBBF24", "Returned": "#FB923C", "Rejected": "#FB7185",
          "Pending": "#64748B", "Blocked": "#F472B6", "Escalated": "#E879F9", "Awaiting farmer": "#2DD4BF",
          "Posted": "#38BDF8", "Verified": "#A78BFA", "Retired": "#34D399", "Reversed": "#F97316",
          "Superseded": "#475569"}
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
                       partners=["GreenLoop Recyclers", "EcoCycle"],
                       parcels={"P-101": dict(loc=(13.05, 77.50), ha=12.5, farmer="R. Gowda", share=60),
                                "P-102": dict(loc=(13.03, 77.45), ha=8.0, farmer="S. Naik", share=60)}),
    "Nova Retail": dict(target=1800, rewards=False, scale=0.6,
                        sites={"Store Hub": (13.02, 77.65), "Warehouse": (12.90, 77.50)},
                        partners=["ReNew Hub", "CleanChain"],
                        parcels={"P-201": dict(loc=(13.00, 77.58), ha=15.0, farmer="M. Rao", share=55)}),
}
ROLES = {
    "Data Collection Team": ("You collect waste and land data from client sites, partners and farms.",
                             ["Log a collection", "Log land practice", "Returned records", "Site map"]),
    "Farmer / Landowner": ("You own or manage enrolled land. You confirm every practice entry. You do not enter data.", ["My parcels", "Confirm practice"]),
    "Platform Admin": ("You check batches, clear flags and post credits.", ["Overview", "Review queue", "Post credits", "Batch trail", "Ledger", "Site map"]),
    "Verifier": ("You check the records and sign off the credits.", ["Verify credits", "Batch trail", "Ledger"]),
    "Client ESG Manager": ("You decide how credits are used against targets.", ["Overview", "Retire credits", "Insights", "Ledger"]),
    "Finance / Management": ("You use reports and budgets to make decisions.", ["Overview", "Insights"]),
}

# ---- waste streams and chain of custody (Module 2A, Module 3) ----
STREAMS = ["Plastic and dry waste", "E-waste", "Organic waste"]
UKEY = {"E-waste": "E-waste", "Organic waste": "Organic"}   # extension streams that need an approved factor
TYPICAL = {"Plastic and dry waste": 400, "E-waste": 600, "Organic waste": 600}   # kg per batch, used until a site has 3 batches of history
E_CATS = ["IT and telecom equipment", "Consumer electronics", "Large household appliances"]
CLAIMS = ["EPR credit and carbon estimate, recorded separately", "EPR credit only", "Carbon estimate only"]
CHAINS = {
    "Plastic and dry waste": ["Waste generator (client site, household, commercial, industrial) segregates plastic by type.",
                              "Informal collector or waste picker gathers and sells material.",
                              "Local aggregator or scrap dealer consolidates, sorts and weighs.",
                              "Collection partner or transporter moves loads to a facility.",
                              "Material recovery facility (MRF) sorts, bales and records yield and contamination.",
                              "Recycler washes, shreds and reprocesses into flakes, granules or finished products.",
                              "End buyer (manufacturer) purchases the recycled output.",
                              "Residue goes to disposal (landfill, incinerator or co-processing)."],
    "E-waste": ["Generator (company, institution, household) hands over end-of-life electronics.",
                "Collection centre or take-back point logs items by category.",
                "Authorised aggregator or transporter moves material under a manifest.",
                "Authorised dismantler or recycler separates components (circuit boards, batteries, plastics, metals).",
                "Recovered metals, plastics and other fractions are sold to refiners and processors.",
                "Hazardous fractions go to authorised treatment, storage and disposal facilities."],
}
STREAM_TABLE = pd.DataFrame([
    ["PET, HDPE", "Weight (kg)", "Yes: plastic EPR credit", "Needs an approved methodology; none is listed for standalone plastic recycling under the CCTS"],
    ["Dry waste", "Weight (kg)", "No (not plastic)", "Estimate only, as in the conversion table"],
    ["E-waste", "Units by category, and weight", "Clearest route", "Depends on a methodology for avoided virgin material production, which needs verification"],
    ["Organic waste", "Weight (kg)", "Not covered here", "Established methodologies exist (landfill methane, compost, biogas); likely the strongest carbon route"],
    ["Agriculture", "Land area (hectares) and practice records", "Not covered here",
     "Rice management, livestock manure methane and tree planting have approved CCTS methodologies (November 2026); soil carbon does not"],
], columns=["Stream", "Counted as", "EPR credit", "Carbon credit"])

# ---- agricultural land and cultivated land (Module 2B) ----
# ok = an approved CCTS offset methodology covers the practice (as stated in the specification, November 2026).
# f = placeholder tCO2e per hectare, b = placeholder buffer. Buffer is higher where stored carbon can be reversed (trees, soil).
PRACTICES = {
    "Rice: alternate wetting and drying": dict(f=1.6, b=0.10, ok=True),
    "Livestock manure methane recovery": dict(f=2.4, b=0.05, ok=True),
    "Tree planting (afforestation or reforestation)": dict(f=3.2, b=0.20, ok=True),
    "Soil carbon: cover crops, reduced tillage": dict(f=0.8, b=0.20, ok=False),
}
LEAK = 0.05   # placeholder, as in the specification's worked example
SEASONS = ["Kharif 2026", "Rabi 2026-27"]
G4_OK = ("G4 passed: green points and EPR credits calculated. Carbon is an indicative estimate only; "
         "no carbon credit is issued without an approved methodology")
VEHICLES = {"Tempo (750 kg)": 750, "Mini truck (2,000 kg)": 2000, "Truck (8,000 kg)": 8000}   # capacity plausibility check
DEFAULT_RULES = {"PET": (10, 1.0, 1.5), "HDPE": (8, 1.0, 1.2), "Dry": (3, 0.0, 0.8), "E-waste": (0, 0.0, 0.0), "Organic": (0, 0.0, 0.0)}

def card(label, value, color="#E5E7EB"):
    return f'<div class="card"><span>{label}</span><b style="color:{color}">{value}</b></div>'
def chip(text, state, color=None):
    return f'<span class="chip" style="background:{color or COL[state]}">{text}</span>'
def style(fig, h=300):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=h, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15))
    return fig
def now():
    return datetime.now().strftime("%d %b, %H:%M")
def qty(r):
    return f"{r['ha']} ha" if r["stream"] == "Land" else f"{r['kg']} kg"

# ---------------- state: rule sets, counters, ledger journal ----------------
for _k, _v in (("ledger", []), ("lot_n", 0), ("sn", 0)):
    st.session_state.setdefault(_k, _v)
if "rules" not in st.session_state:
    st.session_state.rules = dict(DEFAULT_RULES)
    st.session_state.rv = 1
    st.session_state.rhist = [dict(version=1, when=now(), note="Initial placeholder rule set")]
RULES = st.session_state.rules
B = lambda: st.session_state.b

def next_serial(kind):
    st.session_state.sn += 1
    return f"W2C-{kind}-{st.session_state.sn:06d}"

def journal(i, text):
    """Append-only ledger journal. Every status change is a new entry; earlier entries are never edited."""
    r = B().loc[i]
    j = st.session_state.ledger
    j.append(dict(entry=len(j) + 1, when=now(), client=r["client"], record=i, ref=r["lot"] or r["parcel"],
                  event=text, status_after=r["status"], serial=r["serial"]))

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### ♻️ Client")
    client = st.selectbox("Organisation", list(CLIENTS), label_visibility="collapsed")
    cfg = CLIENTS[client]
    st.caption(f"EPR target: {cfg['target']:,} credits | Rewards: {'on' if cfg['rewards'] else 'off'}")
    st.markdown("### 👤 You are")
    role = st.radio("Role", list(ROLES), label_visibility="collapsed")
    with st.expander(f"Conversion rules (placeholders) · v{st.session_state.rv}"):
        if role == "Platform Admin":
            new_rules = {}
            for k, (p, e, c) in st.session_state.rules.items():
                a, b, d3 = st.columns(3)
                new_rules[k] = (a.number_input(f"{k} pts/kg", value=float(p), key=f"p{k}"),
                                b.number_input("EPR", value=float(e), key=f"e{k}"),
                                d3.number_input("CO2e", value=float(c), key=f"c{k}"))
            if new_rules != st.session_state.rules:
                st.session_state.rv += 1
                st.session_state.rules = new_rules
                st.session_state.rhist.append(dict(version=st.session_state.rv, when=now(), note="Edited by the Platform Admin"))
                RULES = st.session_state.rules
            st.caption("Every change creates a new dated rule set. Records keep the version they were calculated with. "
                       "E-waste and Organic have no approved factor yet, so they stay at 0 and gate G4 keeps those batches pending.")
        else:
            st.dataframe(pd.DataFrame([dict(Category=k, **{"Points/kg": v[0], "EPR/kg": v[1], "kg CO2e/kg": v[2]}) for k, v in RULES.items()]),
                         width="stretch", hide_index=True)
            st.caption("Only the Platform Admin can change the rules.")

def convert(net):
    return dict(kg=round(sum(net.values()), 1), points=round(sum(net[k] * RULES[k][0] for k in net)),
                epr=round(sum(net[k] * RULES[k][1] for k in net), 1),
                tco2e=round(sum(net[k] * RULES[k][2] for k in net) / 1000, 3))

def apply_claim(res, claim):
    """EPR claims and carbon claims are recorded separately: a lot claimed under one instrument carries zero of the other."""
    res = dict(res)
    if claim == CLAIMS[1]:
        res["tco2e"] = 0.0
    elif claim == CLAIMS[2]:
        res["epr"] = 0.0
    return res

def is_unset(stream):
    """True when a waste stream has no approved factor yet (all three factors are 0)."""
    k = UKEY.get(stream)
    return k is not None and all(v == 0 for v in RULES[k])

def land_credit(ha, practice):
    """Credits = area x factor x (1 - leakage) x (1 - buffer). Only approved practices are converted."""
    pr = PRACTICES[practice]
    net = ha * pr["f"] * (1 - LEAK)
    return dict(issued=round(net * (1 - pr["b"]), 2) if pr["ok"] else 0.0, buffer=round(net * pr["b"], 2) if pr["ok"] else 0.0)

def check_custody(diff, km, hrs, out, rpct, loss, inv, rcpt):
    """Control gates C1 to C4. Each returns (state, message) with state ok / warn / fail."""
    speed = km / hrs
    tot = out + rpct + loss
    gap = abs(100 - tot)
    if diff <= 2:
        c1 = ("ok", "")
    elif diff <= 5:
        c1 = ("warn", f"weights differ by {diff:.1f}%. Query the giver and receiver")
    else:
        c1 = ("fail", f"weights differ by {diff:.1f}%. Lot excluded from the credit stream")
    if speed <= 70:
        c2 = ("ok", "")
    elif speed <= 110:
        c2 = ("warn", f"average speed {speed:.0f} km/h is high. Review route, time and distance")
    else:
        c2 = ("fail", f"average speed {speed:.0f} km/h is implausible. Lot blocked and escalated to G3")
    if out > 100 or tot > 103:
        c3 = ("fail", "output is more than input. Block and investigate")
    elif gap <= 3:
        c3 = ("ok", "")
    elif gap <= 8:
        c3 = ("warn", f"{gap:.0f}% of the input is unaccounted for. Request corrected weights")
    else:
        c3 = ("fail", f"{gap:.0f}% of the input is unaccounted for. Block and investigate")
    if inv and rcpt:
        c4 = ("ok", "")
    elif inv or rcpt:
        c4 = ("warn", "an invoice or receipt is missing. Request it")
    else:
        c4 = ("fail", "no output invoice or residue receipt. Lot stays pending")
    return dict(C1=c1, C2=c2, C3=c3, C4=c4)

def waste_outcome(g2, cs, risk, unset, lic=""):
    """Where a waste batch goes after the licence check, G2, C1 to C4, G3 and G4.
    Returns (status, trail steps, pending reason, message)."""
    steps = ["Collected by the Data Collection Team", "Entered into the platform"]
    if lic:
        return "Rejected", steps + [f"G1 licence check failed: {lic}. Only registered, licensed actors can appear in a chain"], "", f"Batch rejected: {lic}"
    if not g2:
        return "Returned", steps + ["G2 failed: receipt missing. Returned to the Data Collection Team"], "", "Sent back: receipt missing"
    steps.append("G2 passed: batch is complete")
    if cs["C1"][0] == "fail":
        return "Rejected", steps + [f"C1 failed: {cs['C1'][1]}"], "", "Batch rejected at C1"
    bad = [g for g in ("C2", "C3") if cs[g][0] == "fail"]
    if bad:
        return "Blocked", steps + [f"{g} failed: {cs[g][1]}" for g in bad], "", f"Batch blocked at {' and '.join(bad)}"
    if cs["C4"][0] == "fail":
        return "Pending", steps + [f"C4 failed: {cs['C4'][1]}"], "evidence", "Batch stays pending: evidence missing"
    ret = [g for g in ("C1", "C3", "C4") if cs[g][0] == "warn"]
    if ret:
        return "Returned", steps + [f"{g} flagged: {cs[g][1]}" for g in ret] + ["Returned to the Data Collection Team"], "", "Sent back: custody evidence needed"
    c2warn = cs["C2"][0] == "warn"
    steps.append(f"C2 flagged: {cs['C2'][1]}" if c2warn else "C1 to C4 passed: custody trail complete")
    if risk == "High":
        return "Blocked", steps + ["G3 failed: high risk. Batch blocked for investigation"], "methodology" if unset else "", "Batch blocked at G3 for investigation"
    if risk == "Medium":
        return "Under review", steps + ["G3 flagged: medium risk. Sent to Platform Admin"], "methodology" if unset else "", "Batch sent to the Platform Admin for review"
    if c2warn:
        return "Under review", steps + ["Sent to Platform Admin for a route review"], "methodology" if unset else "", "Batch sent to the Platform Admin for review"
    steps.append("G3 passed: low risk")
    if unset:
        return "Pending", steps + ["G4 blocked: no approved factor for this stream. Record stays pending"], "methodology", "Batch stays pending: no approved factor"
    return "Checked", steps + [G4_OK], "", "Batch passed all checks"

def land_outcome(tenure, overlap, g2, risk, approved):
    """Where a land record goes. Returns (status, trail steps starting with G1, pending reason, message)."""
    if not tenure:
        return "Returned", ["G1 failed: proof of tenure missing. Returned to the Data Collection Team"], "", "Sent back: proof of tenure missing"
    if overlap:
        return "Rejected", ["G1 failed: boundary overlaps another registered parcel"], "", "Record rejected: parcel overlap"
    steps = ["G1 passed: tenure and boundary checked"]
    if not g2:
        return "Returned", steps + ["G2 failed: photo or imagery missing. Returned to the Data Collection Team"], "", "Sent back: evidence missing"
    steps.append("G2 passed: record is complete")
    if risk == "High":
        return "Blocked", steps + ["G3 failed: high risk. Record blocked for investigation"], "" if approved else "methodology", "Record blocked at G3 for investigation"
    if risk == "Medium":
        return "Under review", steps + ["G3 flagged: medium risk. Sent to Platform Admin"], "" if approved else "methodology", "Record sent to the Platform Admin for review"
    steps.append("G3 passed: low risk")
    if not approved:
        return "Pending", steps + ["G4 blocked: no approved methodology. Record stays pending"], "methodology", "Record stays pending: no approved methodology"
    return "Checked", steps + ["G4 passed: approved methodology applied. Buffer held back"], "", "Record passed all checks"

# ---------------- data ----------------
BASE = ["Collected by the Data Collection Team", "Entered into the platform", "G2 passed: batch is complete",
        "C1 to C4 passed: custody trail complete", "G3 passed: low risk", G4_OK]
LAND_BASE = ["Practice logged by the field agent", "Entered into the platform", "G1 passed: tenure and boundary checked",
             "Confirmed by the farmer", "G2 passed: record is complete", "G3 passed: low risk",
             "G4 passed: approved methodology applied. Buffer held back"]
AFTER = {"Posted": ["Posted by the Platform Admin (G5)"], "Verified": ["Posted by the Platform Admin (G5)", "Signed off by the Verifier (G6)"],
         "Retired": ["Posted by the Platform Admin (G5)", "Signed off by the Verifier (G6)", "EPR credits and carbon estimate retired separately by the ESG Manager"]}
DEFAULTS = dict(client="", stream=STREAMS[0], site="", partner="", kg=0.0, points=0, epr=0.0, tco2e=0.0, cont=0, risk="Low", flags="",
                lat=0.0, lon=0.0, status="Checked", trail=None, lot="", units=0, ha=0.0, parcel="", practice="", farmer="", share=0,
                claim=CLAIMS[0], custody="", pend="", nxt="", nxt_steps=None,
                category="", season="", receipt="", gross=0.0, net=None, rv=1, serial="", epr_done=False, co2_done=False)
def new_row(**kw):
    r = dict(DEFAULTS)
    r.update(kw)
    r["trail"] = list(r["trail"] or [])
    r["nxt_steps"] = list(r["nxt_steps"] or [])
    r["net"] = dict(r["net"] or {})
    return r
if "b" not in st.session_state:
    rng = np.random.default_rng(7)
    rows = []
    for cl, c in CLIENTS.items():
        for i in range(8):
            net = {"PET": rng.integers(60, 200), "HDPE": rng.integers(40, 140), "Dry": rng.integers(100, 300)}
            site = str(rng.choice(list(c["sites"])))
            la, lo = c["sites"][site]
            status = ["Retired", "Retired", "Verified", "Verified", "Posted", "Posted", "Checked", "Under review"][i]
            steps = BASE[:] if status != "Under review" else BASE[:4] + ["G3 flagged: medium risk. Sent to Platform Admin"]
            steps += AFTER.get(status, [])
            st.session_state.lot_n += 1
            n = st.session_state.lot_n
            done = status == "Retired"
            res0 = convert(net)
            rows.append(new_row(client=cl, site=site, partner=str(rng.choice(c["partners"])), **res0,
                                cont=int(rng.integers(2, 12)), risk="Medium" if status == "Under review" else "Low",
                                flags="Weight is higher than usual" if status == "Under review" else "",
                                lat=la + rng.normal(0, .004), lon=lo + rng.normal(0, .004), status=status,
                                trail=[f"{2 + j // 4:02d} Nov, 1{i % 6}:{10 + j * 5:02d}|{s}" for j, s in enumerate(steps)],
                                lot=f"LOT-{n:04d}", receipt=f"RCPT-{n:04d}", gross=float(sum(net.values())),
                                net={k: int(v) for k, v in net.items()}, rv=1, epr_done=done, co2_done=done,
                                serial=", ".join(next_serial(k) for k, v in (("EPR", res0["epr"]), ("CO2", res0["tco2e"])) if v > 0) if done else "",
                                custody="C1 ok · C2 ok · C3 ok · C4 ok"))
    for cl, c in CLIENTS.items():
        for k, (pid, p) in enumerate(c["parcels"].items()):
            pr = list(PRACTICES)[k % 3]
            status = ["Verified", "Posted", "Checked"][k % 3]
            steps = LAND_BASE[:] + AFTER.get(status, [])
            rows.append(new_row(client=cl, stream="Land", site=pid, partner="Field team", tco2e=land_credit(p["ha"], pr)["issued"],
                                ha=p["ha"], parcel=pid, practice=pr, season=SEASONS[0], farmer=p["farmer"], share=p["share"],
                                lat=p["loc"][0], lon=p["loc"][1], status=status,
                                trail=[f"{3 + j // 4:02d} Nov, 0{k % 6}:{10 + j * 5:02d}|{s}" for j, s in enumerate(steps)]))
    st.session_state.b = pd.DataFrame(rows)
    for _i in range(len(rows)):
        journal(_i, "Opening entry (demo data)")
def cur():
    d = B()
    return d[d.client == client]
def move(i, status, text):
    B().at[i, "status"] = status
    B().at[i, "trail"].append(f"{now()}|{text}")
    journal(i, text)
def flash(msg):
    st.session_state["flash"] = msg
    st.rerun()
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

# ---------------- pages ----------------
def page_log():
    L, R = st.columns([1, 1.4], gap="large")
    with L:
        stream = st.selectbox("Waste stream", STREAMS)
        site = st.selectbox("Client site", list(cfg["sites"]))
        partner = st.selectbox("Collection partner", cfg["partners"])
        units, cat = 0, ""
        if stream == STREAMS[0]:
            pet = st.slider("PET (kg)", 0, 500, 120)
            hdpe = st.slider("HDPE (kg)", 0, 500, 80)
            dry = st.slider("Dry waste (kg)", 0, 500, 200, help="Clean, dry recyclables other than PET and HDPE, such as other plastics "
                            "(for example PP), paper, cardboard, metal and glass.")
            lines = {"PET": pet, "HDPE": hdpe, "Dry": dry}
        elif stream == "E-waste":
            cat = st.selectbox("E-waste category", E_CATS)
            units = st.slider("Items (units)", 0, 500, 40)
            lines = {"E-waste": st.slider("Weight (kg)", 0, 2000, 250)}
            st.caption("E-waste is counted by unit and category as well as weight. It is hazardous and legally regulated, and only authorised "
                       "recyclers may process it. Check the current E-Waste (Management) Rules before activating this stream for a client.")
        else:
            lines = {"Organic": st.slider("Organic waste (kg)", 0, 2000, 300)}
        cont = st.slider("Contamination (%)", 0, 40, 5)
        up = st.file_uploader("Receipt photo", type=["png", "jpg", "jpeg", "pdf"])
        sample = st.checkbox("Use a sample receipt", True)
        receipt_in = st.text_input("Receipt or weighbridge slip number", value="", placeholder="Leave blank for a new sample receipt")
        st.caption("Seeded receipts look like RCPT-0001. Enter one that is already on the ledger to test the duplicate check.")
        lot = f"LOT-{st.session_state.lot_n + 1:04d}"
        with st.expander(f"Chain of custody (C1 to C4) · {lot}"):
            st.caption("A unique lot ID is created at first collection. Each handover is confirmed by both the giver and the receiver.")
            diff = st.slider("C1: weight difference at handover (%)", 0.0, 15.0, 1.0, 0.5)
            km = st.slider("C2: distance travelled (km)", 1, 400, 60)
            hrs = st.slider("C2: transit time (hours)", 0.5, 24.0, 2.0, 0.5)
            out = st.slider("C3: recycled output (% of input)", 0, 110, 85)
            rpct = st.slider("C3: residue (% of input)", 0, 40, 12)
            loss = st.slider("C3: documented loss (% of input)", 0, 20, 2)
            veh = st.selectbox("Vehicle used (capacity plausibility check at G3)", list(VEHICLES))
            inv = st.checkbox("C4: invoice for recycled output attached", True)
            rcpt = st.checkbox("C4: residue disposal receipt attached", True)
            claim = st.selectbox("Instrument this lot is claimed under", CLAIMS)
            if stream in CHAINS:
                st.markdown("**Chain for this stream**")
                st.markdown("\n".join(f"{n}. {s}" for n, s in enumerate(CHAINS[stream], 1)))
            else:
                st.caption("The chain steps for organic waste are not defined in the specification yet.")
        with st.expander("Try a fraud case"):
            dup = st.toggle("Receipt already used", False)
            wrong = st.toggle("Collected away from the site", False)
            t_diff = st.toggle("Receiver weighs much less than the giver", False)
            t_ghost = st.toggle("Vehicle seen at two places at once", False)
            t_grow = st.toggle("Output weight is more than input", False)
            noparent = st.toggle("Lot has no parent record", False)
            unlic = st.toggle("A chain actor is not registered or licensed", False)
            double = st.toggle("Same tonnes claimed for EPR by one party and for carbon by another", False)
            selfdeal = st.toggle("Partner is linked to the collection team or the client site", False)
            unauth = st.toggle("Recycler is not authorised for e-waste", False) if stream == "E-waste" else False
    if t_diff:
        diff = 9.0
    if t_ghost:
        km, hrs = 250, 0.5
    if t_grow:
        out = 110
    f = 1 - cont / 100
    net = {k: v * f for k, v in lines.items()}
    total = sum(lines.values())
    res = apply_claim(convert(net), claim)
    g2 = (up is not None) or sample
    receipt = (receipt_in.strip() or lot.replace("LOT", "RCPT")) if g2 else ""
    allb = B()
    live = ~allb.status.isin(["Rejected", "Superseded"])
    used = set(allb.loc[(allb.receipt != "") & live, "receipt"])
    dup_real = bool(receipt) and receipt in used
    # weight spike: compared with this site's own history once it has 3 batches, otherwise with a typical batch for the stream
    hist = allb[(allb.client == client) & (allb.site == site) & (allb.stream == stream) & live & (allb.gross > 0)]
    usual = float(hist.gross.mean()) if len(hist) >= 3 else float(TYPICAL[stream])
    ph = allb[(allb.partner == partner) & live & (allb.gross > 0)].tail(3)
    round_flag = total > 0 and total % 50 == 0 and len(ph) >= 3 and bool((ph.gross % 50 == 0).all())
    pet_share = stream == STREAMS[0] and total > 0 and lines["PET"] / total > 0.65
    lic = "a chain actor is not registered or licensed" if unlic else "the recycler is not authorised to process e-waste" if unauth else ""
    flags, score = [], 0
    for cond, pts, msg in [(dup or dup_real, 60, "Receipt was used before"),
                           (total > 3 * usual, 40, f"Weight is {total / usual:.1f}x the usual {usual:.0f} kg for this site"),
                           (wrong, 30, "Location does not match the site"), (cont > 15, 20, "Contamination is high"),
                           (noparent, 40, "Lot has no parent record"),
                           (total > VEHICLES[veh], 40, f"Weight of {total:,.0f} kg is more than a {veh.split(' (')[0].lower()} can carry ({VEHICLES[veh]:,} kg)"),
                           (selfdeal, 35, "Partner is linked to the collection team or the client site (self-dealing check)"),
                           (double, 50, "Same tonnes claimed for EPR by one party and for carbon by another"),
                           (round_flag, 20, "Repeated round-number weights from this partner"),
                           (pet_share, 15, "Unusually high share of PET (high-value category)")]:
        if cond:
            score += pts
            flags.append(msg)
    risk = "Low" if score < 20 else "Medium" if score < 50 else "High"
    cs = check_custody(diff, km, hrs, out, rpct, loss, inv, rcpt)
    cflags = [f"{g}: {m}" for g, (s, m) in cs.items() if s != "ok"]
    status, steps, pend, msg = waste_outcome(g2, cs, risk, is_unset(stream), lic)
    custody_bad = any(v[0] == "fail" for v in cs.values())
    s1 = "fail" if lic else "ok"
    s2 = "ok" if g2 else "fail"
    s3 = "idle" if (lic or not g2 or custody_bad) else {"Low": "ok", "Medium": "warn", "High": "fail"}[risk]
    s4 = "ok" if status == "Checked" else "warn" if (status == "Pending" and pend == "methodology") else "idle"
    with R:
        cchips = "".join(chip(f"{g} {nm}", "idle" if (lic or not g2) else cs[g][0]) for g, nm in
                         [("C1", "Handover"), ("C2", "Transit"), ("C3", "Mass balance"), ("C4", "Outputs")])
        st.markdown(chip("G1 Licence", s1) + chip("G2 Complete", s2) + cchips + chip(f"G3 Fraud check: {risk}", s3) + chip("G4 Credits", s4), unsafe_allow_html=True)
        if lic:
            st.error(f"Gate G1 licence check failed: {lic}. Only registered, licensed actors can appear in a chain, so the batch will be rejected.")
        if not g2:
            st.error("Receipt is missing. The batch will go back to the Data Collection Team.")
        for fl in cflags + flags:
            st.warning(fl)
        if risk == "High" and not lic:
            st.error("High risk: gate G3 will block this batch for investigation.")
        if is_unset(stream):
            st.info("No approved factor is set for this stream (see Conversion rules in the sidebar). Gate G4 will keep the batch pending.")
        c1, c2, c3 = st.columns(3)
        c1.markdown(card("Green points", f"{res['points']:,}", COL["Dry"]), unsafe_allow_html=True)
        c2.markdown(card("EPR credits", f"{res['epr']:,}", COL["PET"]), unsafe_allow_html=True)
        c3.markdown(card("tCO2e (est.)", res["tco2e"], COL["HDPE"]), unsafe_allow_html=True)
        st.caption("Carbon figures are indicative estimates. Gate G4 does not issue a carbon credit for PET, HDPE or dry waste, because no approved "
                   "methodology applies. Green points and EPR credits are not affected.")
        if stream == STREAMS[0]:
            sk = go.Figure(go.Sankey(
                node=dict(label=["PET", "HDPE", "Dry waste", "Green points", "EPR credits", "Carbon offset"], pad=16, thickness=14,
                          color=[COL["PET"], COL["HDPE"], COL["Dry"], "#FBBF24", "#38BDF8", "#A78BFA"]),
                link=dict(source=[0, 1, 2, 0, 1, 0, 1, 2], target=[3, 3, 3, 4, 4, 5, 5, 5],
                          value=[net["PET"], net["HDPE"], net["Dry"], net["PET"], net["HDPE"], net["PET"], net["HDPE"], net["Dry"]],
                          color=["rgba(148,163,184,.25)"] * 8)))
            st.plotly_chart(style(sk, 230), width="stretch")
        with st.expander("How each stream is counted and which credit it can earn"):
            st.dataframe(STREAM_TABLE, width="stretch", hide_index=True)
            st.caption("Plastic credits (tonnes of plastic) and carbon credits (tCO2e) are different units and must never be combined. "
                       "EPR claims and carbon claims for the same tonne are recorded separately, with a note of which instrument each tonne is claimed under.")
        if st.button("Submit batch", type="primary", disabled=res["kg"] <= 0):
            la, lo = cfg["sites"][site]
            off = 0.06 if wrong else 0
            row = new_row(client=client, stream=stream, site=site, partner=partner, **res, cont=cont, risk=risk,
                          flags="; ".join(cflags + flags), lat=la + off, lon=lo + off, status=status,
                          trail=[f"{now()}|{s}" for s in steps], lot=lot, units=units, category=cat, claim=claim,
                          custody=" · ".join(f"{g} {v[0]}" for g, v in cs.items()), pend=pend,
                          receipt=receipt, gross=float(total), net={k: float(v) for k, v in net.items()}, rv=st.session_state.rv)
            st.session_state.b = pd.concat([B(), pd.DataFrame([row])], ignore_index=True)
            st.session_state.lot_n += 1
            journal(len(B()) - 1, "Submitted. " + msg)
            flash(msg)

def page_land():
    parcels = cfg["parcels"]
    L, R = st.columns([1, 1.4], gap="large")
    with L:
        pid = st.selectbox("Parcel", list(parcels), format_func=lambda k: f"{k} · {parcels[k]['farmer']} · {parcels[k]['ha']} ha")
        p = parcels[pid]
        practice = st.selectbox("Practice or planting event", list(PRACTICES))
        season = st.selectbox("Season", SEASONS)
        ha = st.number_input("Area covered (ha)", min_value=0.5, max_value=float(p["ha"]) * 1.5, value=float(p["ha"]), step=0.5)
        tenure = st.checkbox("Proof of tenure on file", True)
        photo = st.checkbox("Geo-tagged photo from the field visit", True)
        imagery = st.checkbox("Satellite imagery attached", True)
        with st.expander("Try a fraud case"):
            overlap = st.toggle("Boundary overlaps another registered parcel", False)
            contra = st.toggle("Satellite imagery contradicts the practice log", False)
            fert = st.toggle("Fertiliser purchases do not match the area and practice", False)
            bulk = st.toggle("Practice records are identical across many farms or entered in bulk on one day", False)
            double = st.toggle("Same land claimed in another scheme or registry", False)
            st.caption("Raise the area above the land record to test the area check.")
    approved = PRACTICES[practice]["ok"]
    area_used = min(ha, p["ha"])   # credits are only calculated on the area in the land record
    lc = land_credit(area_used, practice)
    allb = B()
    dup_season = bool(((allb.stream == "Land") & (allb.parcel == pid) & (allb.practice == practice) & (allb.season == season)
                       & ~allb.status.isin(["Rejected", "Returned", "Reversed", "Superseded"])).any())
    flags, score = [], 0
    for cond, pts, msg in [(ha > p["ha"], 40, "Area is larger than the land record"),
                           (dup_season, 60, "A record for this parcel, practice and season already exists"),
                           (contra, 50, "Satellite imagery contradicts the practice log"),
                           (fert, 30, "Fertiliser purchases do not match the area and practice claimed"),
                           (bulk, 30, "Practice records are identical across many farms or entered in bulk on one day"),
                           (double, 60, "Same land claimed in another scheme or registry")]:
        if cond:
            score += pts
            flags.append(msg)
    risk = "Low" if score < 20 else "Medium" if score < 50 else "High"
    g1 = tenure and not overlap
    g2 = photo and imagery
    status, steps, pend, msg = land_outcome(tenure, overlap, g2, risk, approved)
    s1 = "ok" if g1 else "fail"
    s2 = "idle" if not g1 else "ok" if g2 else "fail"
    s3 = "idle" if not (g1 and g2) else {"Low": "ok", "Medium": "warn", "High": "fail"}[risk]
    s4 = "idle" if not (g1 and g2 and risk == "Low") else "ok" if approved else "warn"
    with R:
        st.markdown(chip("G1 Tenure and boundary", s1) + chip("G2 Complete", s2) + chip(f"G3 Fraud check: {risk}", s3) + chip("G4 Methodology", s4), unsafe_allow_html=True)
        if not tenure:
            st.error("Proof of tenure is missing. The record goes back to the Data Collection Team.")
        if overlap:
            st.error("The boundary overlaps another registered parcel. Gate G1 rejects the record.")
        if g1 and not g2:
            st.error("A photo or satellite imagery is missing. The record goes back to the Data Collection Team.")
        for fl in flags:
            st.warning(fl)
        if risk == "High" and g1 and g2:
            st.error("High risk: gate G3 will block this record for investigation.")
        if ha > p["ha"]:
            st.info(f"The claimed {ha:,.1f} ha is above the land record of {p['ha']:,.1f} ha. Credits are calculated on the record area only.")
        if not approved:
            st.info("No approved CCTS methodology covers this practice (agricultural soil carbon). Gate G4 will keep the record pending.")
        if practice == "Livestock manure methane recovery":
            st.info("The approved methodology (BM AG04.001) covers manure management at households and small farms. It is not defined per hectare; "
                    "it typically counts the manure managed and the methane recovered. The per-hectare factor here is a demo placeholder only.")
        c1, c2, c3 = st.columns(3)
        c1.markdown(card("Area credited (ha)", f"{area_used:,.1f}", COL["Dry"]), unsafe_allow_html=True)
        c2.markdown(card("tCO2e issued (est.)", f"{lc['issued']:,.2f}", COL["HDPE"]), unsafe_allow_html=True)
        c3.markdown(card("Held back as buffer", f"{lc['buffer']:,.2f}", COL["warn"]), unsafe_allow_html=True)
        st.caption(f"Credits = area × factor × (1 − {LEAK:.0%} leakage) × (1 − buffer). The buffer here is {PRACTICES[practice]['b']:.0%}; it is higher for "
                   "practices where stored carbon can be lost (trees, soil). Factors, leakage and buffer are demo placeholders. "
                   "As of November 2026 the specification lists approved methodologies for rice management, livestock manure methane and tree planting, and none for agricultural soil carbon.")
        st.caption("Land has no handover chain, so gates C1 to C4 do not apply. The parcel and practice checks sit in G1, G2 and G3.")
        if st.button("Submit practice record", type="primary"):
            first = ["Practice logged by the field agent", "Entered into the platform"]
            if g1:
                final, final_steps = "Awaiting farmer", first + steps[:1]
                nxt, nxt_steps = status, steps[1:]
            else:
                final, final_steps, nxt, nxt_steps = status, first + steps, "", []
            row = new_row(client=client, stream="Land", site=pid, partner="Field team", tco2e=lc["issued"], risk=risk,
                          flags="; ".join(flags), ha=float(area_used), parcel=pid, practice=practice, season=season,
                          farmer=p["farmer"], share=p["share"],
                          lat=p["loc"][0], lon=p["loc"][1], status=final, trail=[f"{now()}|{s}" for s in final_steps],
                          pend=pend, nxt=nxt, nxt_steps=nxt_steps)
            st.session_state.b = pd.concat([B(), pd.DataFrame([row])], ignore_index=True)
            journal(len(B()) - 1, "Submitted. " + ("Waiting for the farmer to confirm" if g1 else msg))
            flash("Practice logged. Waiting for the farmer to confirm" if g1 else msg)

def page_returned():
    d = cur()
    q = d[d.status == "Returned"]
    if q.empty:
        st.success("No returned records.")
        return
    st.caption("Corrections are new entries, never edits. Close the returned record, then log the corrected one from the collection or land page.")
    for i, r in q.iterrows():
        with st.container(border=True):
            a, b = st.columns([3.2, 1.2])
            why = " · ".join(s.split("|", 1)[1] for s in r.trail[-2:])
            a.markdown(f"**#{i} · {r.site}** · {r.partner} · {qty(r)}  \n:orange[Returned]: {why}")
            if b.button("Close and log a corrected entry", key=f"sup{i}", width="stretch"):
                move(i, "Superseded", "Closed. The correction is logged as a new entry and the original is never edited")
                flash(f"Record #{i} closed. Log the corrected entry next")

def page_parcels():
    d = cur()
    land = d[d.stream == "Land"]
    farmers = sorted({v["farmer"] for v in cfg["parcels"].values()})
    me = st.selectbox("Farmer or landowner", farmers, key="who_parcels")
    reg = pd.DataFrame([dict(Parcel=k, Hectares=v["ha"], Share=f"{v['share']}%") for k, v in cfg["parcels"].items() if v["farmer"] == me])
    st.markdown("**Registered parcels**")
    st.dataframe(reg, width="stretch", hide_index=True)
    mine = land[land.farmer == me]
    posted = mine[mine.status.isin(["Posted", "Verified", "Retired"])]
    share_t = float((posted.tco2e * posted["share"] / 100).sum())
    a, b, c = st.columns(3)
    a.markdown(card("Practice records", len(mine), COL["PET"]), unsafe_allow_html=True)
    b.markdown(card("Credits posted (tCO2e)", f"{posted.tco2e.sum():,.2f}", COL["HDPE"]), unsafe_allow_html=True)
    c.markdown(card("Revenue-share basis (tCO2e)", f"{share_t:,.2f}", COL["Dry"]), unsafe_allow_html=True)
    if mine.empty:
        st.info("No practice records for your parcels yet.")
        return
    st.dataframe(mine[["parcel", "practice", "season", "ha", "status", "tco2e", "share"]].rename(columns={"ha": "hectares", "share": "your revenue share %"}),
                 width="stretch", hide_index=True)
    st.caption("The agreed revenue share is recorded in the ledger against the credits it relates to. Your share is a percentage of the revenue "
               "from the credits, not a number of credits. The tCO2e figure above is the amount that percentage applies to; the money depends on the "
               "price when the credits are sold.")

def page_confirm():
    d = cur()
    farmers = sorted({v["farmer"] for v in cfg["parcels"].values()})
    me = st.selectbox("Farmer or landowner", farmers, key="who_confirm")
    q = d[(d.stream == "Land") & (d.status == "Awaiting farmer") & (d.farmer == me)]
    if q.empty:
        st.success("Nothing to confirm right now.")
        return
    for i, r in q.iterrows():
        with st.container(border=True):
            a, b, c = st.columns([2.4, 1, 1])
            a.markdown(f"**#{i} · {r['parcel']}** · {r['ha']} ha · {r['season']}  \n{r['practice']}")
            if b.button("Confirm", key=f"fc{i}", type="primary", width="stretch"):
                B().at[i, "trail"].extend([f"{now()}|{s}" for s in ["Confirmed by the farmer"] + list(B().at[i, "nxt_steps"])])
                B().at[i, "status"] = B().at[i, "nxt"]
                journal(i, "Confirmed by the farmer")
                flash(f"Entry #{i} confirmed")
            if c.button("Dispute", key=f"fd{i}", width="stretch"):
                move(i, "Returned", "Farmer disputed the entry. Returned to the field agent")
                flash(f"Entry #{i} sent back to the field agent")

def page_map():
    d = cur()
    fig = go.Figure()
    sites = cfg["sites"]
    parcels = cfg["parcels"]
    fig.add_trace(go.Scattermap(lat=[v[0] for v in sites.values()], lon=[v[1] for v in sites.values()], mode="markers+text",
                                text=list(sites), textposition="top right", marker=dict(size=22, color="#64748B"), name="Client sites"))
    fig.add_trace(go.Scattermap(lat=[v["loc"][0] for v in parcels.values()], lon=[v["loc"][1] for v in parcels.values()], mode="markers+text",
                                text=list(parcels), textposition="top right", marker=dict(size=22, color="#84CC16"), name="Land parcels"))
    for s, g in d.groupby("status"):
        label = np.where(g.stream == "Land", g.site + " | " + g.ha.astype(str) + " ha", g.site + " | " + g.kg.astype(str) + " kg")
        fig.add_trace(go.Scattermap(lat=g.lat, lon=g.lon, mode="markers", marker=dict(size=11, color=STATUS[s]), name=s, text=label))
    pts = list(sites.values()) + [v["loc"] for v in parcels.values()]
    fig.update_layout(map=dict(style="carto-darkmatter", center=dict(lat=np.mean([v[0] for v in pts]), lon=np.mean([v[1] for v in pts])), zoom=10.5))
    st.plotly_chart(style(fig, 460), width="stretch")
    st.caption("Grey circles are client sites and green circles are land parcels. A dot far from its site means the location did not match.")

def page_overview():
    d = cur()
    ok = d[d.status.isin(["Posted", "Verified", "Retired"])]
    t = st.columns(5)
    items = [("Waste collected (kg)", f"{d[~d.status.isin(['Rejected', 'Superseded', 'Returned'])].kg.sum():,.0f}", COL["Dry"]),
             ("Green points", f"{ok.points.sum():,}" if cfg["rewards"] else "Off", "#FBBF24"),
             ("EPR credits", f"{ok.epr.sum():,.0f}", COL["PET"]), ("tCO2e (est.)", f"{ok.tco2e.sum():.2f}", COL["HDPE"]),
             ("Batches with issues", int(d.status.isin(["Under review", "Returned", "Rejected", "Blocked", "Escalated", "Pending"]).sum()), COL["fail"])]
    for c, (a, b, k) in zip(t, items):
        c.markdown(card(a, b, k), unsafe_allow_html=True)
    land = d[d.stream == "Land"]
    if not land.empty:
        live = land[~land.status.isin(["Rejected", "Returned", "Reversed", "Superseded"])]
        enrolled = live.ha.sum()
        done = live[live.status.isin(["Verified", "Retired"])].ha.sum()
        cov = f"{done / enrolled:.0%}" if enrolled else "0%"
        credits = land[land.status.isin(["Posted", "Verified", "Retired"])].tco2e.sum()
        lt = st.columns(3)
        for c, (a, b, k) in zip(lt, [("Land enrolled (ha)", f"{enrolled:,.1f}", COL["Dry"]), ("Practice coverage (verified)", cov, COL["PET"]),
                                     ("Land credits (tCO2e)", f"{credits:,.1f}", COL["HDPE"])]):
            c.markdown(card(a, b, k), unsafe_allow_html=True)
    L, R = st.columns(2, gap="large")
    with L:
        retired = d.loc[d.epr_done & (d.stream != "Land"), "epr"].sum()
        g = go.Figure(go.Indicator(mode="gauge+number", value=retired, title={"text": "EPR retired vs target"},
                                   gauge=dict(axis=dict(range=[0, cfg["target"]]), bar=dict(color=COL["PET"]), bgcolor="rgba(255,255,255,.06)", borderwidth=0)))
        st.plotly_chart(style(g, 270), width="stretch")
    with R:
        p = d[~d.status.isin(["Rejected", "Superseded"]) & (d.stream != "Land")].groupby("partner", as_index=False).agg(kg=("kg", "sum"), clean=("cont", "mean"))
        fig = px.bar(p, x="partner", y="kg", color="clean", title="Partner performance (colour = contamination %)",
                     color_continuous_scale=["#34D399", "#FBBF24", "#FB7185"])
        st.plotly_chart(style(fig, 270), width="stretch")
    A, M, S = st.columns(3, gap="large")
    with A:
        order = ["Pending", "Checked", "Posted", "Verified", "Retired"]
        fun = pd.DataFrame({"Status": order, "Batches": [int((d.status == s).sum()) for s in order]})
        st.plotly_chart(style(px.bar(fun, x="Status", y="Batches", color="Status", color_discrete_map=STATUS, title="Credit funnel (records by status)"), 260), width="stretch")
    with M:
        mix = {"PET": 0.0, "HDPE": 0.0, "Dry waste": 0.0}
        for n in d[(d.stream == STREAMS[0]) & ~d.status.isin(["Rejected", "Superseded", "Returned"])].net:
            mix["PET"] += float(n.get("PET", 0))
            mix["HDPE"] += float(n.get("HDPE", 0))
            mix["Dry waste"] += float(n.get("Dry", 0))
        mixdf = pd.DataFrame({"Category": list(mix), "kg": list(mix.values())})
        st.plotly_chart(style(px.pie(mixdf, names="Category", values="kg", hole=.55, color="Category", title="Category mix (net kg)",
                                     color_discrete_map={"PET": COL["PET"], "HDPE": COL["HDPE"], "Dry waste": COL["Dry"]}), 260), width="stretch")
    with S:
        if cfg["rewards"]:
            lb = d[(d.stream != "Land") & ~d.status.isin(["Rejected", "Superseded", "Returned"])].groupby("site", as_index=False).agg(points=("points", "sum"))
            lb = lb.sort_values("points", ascending=True)
            st.plotly_chart(style(px.bar(lb, x="points", y="site", orientation="h", title="Site leaderboard (green points)"), 260), width="stretch")
        else:
            st.info("Rewards are off for this client, so there is no leaderboard.")
    rep = d[d.status.isin(["Verified", "Retired"])][["lot", "parcel", "stream", "site", "partner", "kg", "ha", "points", "epr", "tco2e", "status", "serial", "rv"]]
    st.download_button("⬇️ Download compliance report (verified credits)", rep.to_csv(index=False), "compliance_report.csv", "text/csv")

def page_queue():
    d = cur()
    q = d[d.status.isin(["Under review", "Blocked", "Escalated"])]
    pend = d[d.status == "Pending"]
    if q.empty and pend.empty:
        st.success("Nothing to review right now.")
    for i, r in q.iterrows():
        with st.container(border=True):
            tag = ":red[Blocked]" if r.status == "Blocked" else ":violet[Escalated]" if r.status == "Escalated" else f":orange[{r.risk} risk]"
            st.markdown(f"**#{i} · {r.site}** · {r.partner} · {qty(r)}  \n{tag}: {r['flags'] or 'Needs a second look'}")
            why = st.text_input("Reason for your decision (required)", key=f"why{i}")
            b, c, e = st.columns(3)
            act = None
            if b.button("Clear flags", key=f"c{i}", width="stretch"):
                act = "clear"
            if c.button("Reject", key=f"r{i}", width="stretch"):
                act = "reject"
            if r.status != "Escalated" and e.button("Escalate", key=f"x{i}", width="stretch"):
                act = "escalate"
            if act and not why.strip():
                st.error("Enter a reason first. Every decision is recorded with one.")
            elif act:
                note = why.strip().replace("|", "/")
                if act == "clear":
                    if r["pend"] == "methodology":
                        move(i, "Pending", f"Platform Admin cleared the flags. Reason: {note}. G4 blocked: no approved methodology or factor. Record stays pending")
                    else:
                        move(i, "Checked", f"Platform Admin cleared the flags. Reason: {note}")
                    flash(f"Batch #{i} cleared")
                elif act == "reject":
                    extra = ". Related credits reversed and the partner is flagged for suspension review" if r["risk"] == "High" else ""
                    move(i, "Rejected", f"Platform Admin rejected the batch. Reason: {note}{extra}")
                    flash(f"Batch #{i} rejected")
                else:
                    move(i, "Escalated", f"Escalated by the Platform Admin. Reason: {note}")
                    flash(f"Batch #{i} escalated")
    for i, r in pend.iterrows():
        with st.container(border=True):
            a, b = st.columns([3.2, 1])
            if r["pend"] == "evidence":
                a.markdown(f"**#{i} · {r.site}** · {r.partner} · {qty(r)}  \n:gray[Pending]: the output invoice and residue receipt are missing (C4)")
                if b.button("Evidence received", key=f"e{i}", width="stretch"):
                    if r["risk"] == "High":
                        move(i, "Blocked", "Custody evidence received. C4 passed. G3 failed: high risk. Batch blocked for investigation")
                    elif r["risk"] != "Low":
                        move(i, "Under review", f"Custody evidence received. C4 passed. G3 flagged: {r['risk'].lower()} risk. Sent to Platform Admin")
                    elif is_unset(r["stream"]):
                        B().at[i, "pend"] = "methodology"
                        move(i, "Pending", "Custody evidence received. C4 passed. G4 blocked: no approved factor. Record stays pending")
                    else:
                        move(i, "Checked", f"Custody evidence received. C4 passed. G3 passed: low risk. {G4_OK}")
                    flash(f"Batch #{i} updated")
            else:
                a.markdown(f"**#{i} · {r.site}** · {r.partner} · {qty(r)}  \n:gray[Pending]: no approved methodology or factor yet. Credits stay at 0 until one is approved.")
                if r["stream"] != "Land" and not is_unset(r["stream"]):
                    if b.button(f"Re-run G4 (rule set v{st.session_state.rv})", key=f"g4{i}", width="stretch"):
                        res = apply_claim(convert(r["net"]), r["claim"])
                        for k, v in res.items():
                            B().at[i, k] = v
                        B().at[i, "pend"] = ""
                        B().at[i, "rv"] = st.session_state.rv
                        move(i, "Checked", f"G4 re-run with rule set v{st.session_state.rv}: credits calculated")
                        flash(f"Batch #{i} re-calculated")
    n = int((d.status == "Returned").sum())
    if n:
        st.caption(f"{n} record(s) were returned to the Data Collection Team for missing items.")

def page_post():
    d = cur()
    land = d[(d.stream == "Land") & d.status.isin(["Posted", "Verified", "Retired"])]
    if not land.empty:
        with st.expander("Reverse land credits (practice reversed or carbon lost)"):
            j = st.selectbox("Land batch", list(land.index), key="rev_sel",
                             format_func=lambda i: f"#{i} · {d.at[i, 'parcel']} · {d.at[i, 'practice']} · {d.at[i, 'status']}")
            if st.button("Reverse credits", key="rev_btn"):
                move(j, "Reversed", "Practice reversed or carbon lost. Credits reversed as a new ledger entry")
                flash(f"Batch #{j} reversed")
    q = d[d.status == "Checked"]
    if q.empty:
        st.info("No checked batches are waiting to be posted.")
        return
    st.dataframe(q[["stream", "site", "partner", "kg", "ha", "points", "epr", "tco2e"]], width="stretch")
    if st.button("Approve and post all (G5)", type="primary"):
        for i, r in q.iterrows():
            move(i, "Posted", "Posted by the Platform Admin (G5)" + (". Buffer already held back" if r["stream"] == "Land" else ""))
        flash(f"{len(q)} batch(es) posted to the client ledger")

def page_verify():
    q = cur()[cur().status == "Posted"]
    if q.empty:
        st.info("No posted credits are waiting for sign-off.")
        return
    st.dataframe(q[["stream", "site", "partner", "kg", "ha", "epr", "tco2e", "cont"]].rename(columns={"cont": "contamination %"}), width="stretch")
    if st.button("Sign off these credits (G6)", type="primary"):
        for i in q.index:
            move(i, "Verified", "Signed off by the Verifier (G6)")
        flash(f"{len(q)} batch(es) verified")

def retire_lots(idx, kind):
    """Retire whole lots under one instrument (EPR or CO2). A record becomes Retired only when every instrument it carries is retired."""
    for i in idx:
        s = next_serial(kind)
        old = B().at[i, "serial"]
        B().at[i, "serial"] = f"{old}, {s}" if old else s
        B().at[i, "epr_done" if kind == "EPR" else "co2_done"] = True
        r = B().loc[i]
        full = (r["epr"] <= 0 or r["epr_done"]) and (r["tco2e"] <= 0 or r["co2_done"])
        what = "EPR credits retired against the EPR target" if kind == "EPR" else "Carbon estimate retired to the sustainability pool"
        move(i, "Retired" if full else "Verified", f"{what} by the ESG Manager. Serial {s}")

def page_retire():
    d = cur()
    ver = d[(d.status == "Verified") & (d.epr > 0) & (~d.epr_done) & (d.stream != "Land")]
    co2 = d[(d.status == "Verified") & (d.tco2e > 0) & (~d.co2_done)]
    L, R = st.columns([1, 1.2], gap="large")
    with L:
        st.markdown(card("Verified EPR credits available", f"{ver.epr.sum():,.0f}", COL["HDPE"]), unsafe_allow_html=True)
        if ver.empty:
            st.info("Credits must be verified before they can be retired.")
        else:
            pick = st.multiselect("Lots to retire against the EPR target", list(ver.index), default=list(ver.index),
                                  format_func=lambda i: f"#{i} · {d.at[i, 'lot']} · {d.at[i, 'epr']:,.0f} credits")
            st.caption(f"Selected: {d.loc[pick, 'epr'].sum():,.0f} credits across {len(pick)} lot(s). Whole lots are retired, so the total is exactly what you select.")
            if st.button("Retire against the EPR target", type="primary", disabled=not pick):
                retire_lots(pick, "EPR")
                flash("EPR credits retired")
        st.markdown(card("Verified carbon estimates (tCO2e)", f"{co2.tco2e.sum():,.2f}", COL["Dry"]), unsafe_allow_html=True)
        st.caption("Waste figures are estimates, not carbon credits. Land figures come from an approved methodology.")
        if not co2.empty:
            pick2 = st.multiselect("Lots to retire to the sustainability pool", list(co2.index), default=list(co2.index),
                                   format_func=lambda i: f"#{i} · {d.at[i, 'lot'] or d.at[i, 'parcel']} · {d.at[i, 'tco2e']:,.2f} tCO2e")
            if st.button("Retire carbon estimates", disabled=not pick2):
                retire_lots(pick2, "CO2")
                flash("Carbon estimates retired")
        if cfg["rewards"]:
            st.markdown(card("Green points given to employees", f"{d[d.status.isin(['Posted', 'Verified', 'Retired'])].points.sum():,}", COL["Dry"]), unsafe_allow_html=True)
    with R:
        retired = d.loc[d.epr_done & (d.stream != "Land"), "epr"].sum()
        g = go.Figure(go.Indicator(mode="gauge+number", value=retired, title={"text": "EPR retired vs target"},
                                   gauge=dict(axis=dict(range=[0, cfg["target"]]), bar=dict(color=COL["Dry"]), bgcolor="rgba(255,255,255,.06)", borderwidth=0)))
        st.plotly_chart(style(g, 300), width="stretch")
        st.caption("EPR credits and carbon estimates are retired separately, each with its own serial number.")

def page_trail():
    d = cur()
    i = st.selectbox("Choose a batch", d.index[::-1],
                     format_func=lambda i: f"#{i} · {d.at[i, 'site']} · " + (f"{d.at[i, 'ha']} ha" if d.at[i, "stream"] == "Land" else f"{d.at[i, 'kg']} kg") + f" · {d.at[i, 'status']}")
    r = d.loc[i]
    L, R = st.columns([1, 1.3], gap="large")
    with L:
        st.markdown(chip(r.status, "ok", STATUS[r.status]), unsafe_allow_html=True)
        st.markdown(card("Green points", f"{r.points:,}", COL["Dry"]) + card("EPR credits", f"{r.epr:,}", COL["PET"]) + card("tCO2e (est.)", r.tco2e, COL["HDPE"]), unsafe_allow_html=True)
        if r["stream"] == "Land":
            st.caption(f"Parcel {r['parcel']} · {r['ha']} ha · {r['practice']} · {r['season']} · {r['farmer']} · farmer revenue share {r['share']}%")
        else:
            extra = f" · {r['units']} items ({r['category']})" if r["units"] else ""
            st.caption(f"{r['lot']} · {r['stream']}{extra} · Receipt {r['receipt'] or 'n/a'} · Custody: {r['custody']} · Claimed under: {r['claim']} · Rule set v{r['rv']}")
        if r["serial"]:
            st.caption(f"Retirement serial numbers: {r['serial']}")
    with R:
        html = ""
        for s in r.trail:
            when, text = s.split("|", 1)
            low = text.lower()
            c = COL["fail"] if any(w in low for w in ["failed", "rejected", "blocked", "disputed", "reversed"]) else COL["warn"] if any(w in low for w in ["flagged", "cleared", "returned", "escalated"]) else COL["ok"]
            html += f'<div style="display:flex;gap:12px;margin-bottom:12px"><div style="width:12px;height:12px;border-radius:50%;background:{c};margin-top:5px;flex:none"></div><div><b>{text}</b><br><span style="color:#9CA3AF;font-size:.78rem">{when}</span></div></div>'
        st.markdown(html, unsafe_allow_html=True)

def page_ledger():
    st.caption("Append-only journal. Every status change is a new entry; earlier entries are never edited or deleted.")
    entries = [e for e in st.session_state.ledger if e["client"] == client]
    if not entries:
        st.info("No ledger entries yet.")
        return
    df = pd.DataFrame(entries[::-1]).drop(columns=["client"])
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button("⬇️ Download ledger statement", df.to_csv(index=False), "ledger_statement.csv", "text/csv")
    with st.expander("Rule set history"):
        st.dataframe(pd.DataFrame(st.session_state.rhist), width="stretch", hide_index=True)

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
    fig.add_scatter(x=months[:12], y=hist, name="Collected (kg, demo)", line=dict(color=COL["Dry"], width=3))
    fig.add_scatter(x=months[11:], y=np.r_[hist[-1], fc], name="Forecast", line=dict(color=COL["HDPE"], width=3, dash="dash"))
    fig.add_scatter(x=months[12:], y=fc * 1.1, line=dict(width=0), showlegend=False)
    fig.add_scatter(x=months[12:], y=fc * 0.9, fill="tonexty", fillcolor="rgba(167,139,250,.2)", line=dict(width=0), name="Range")
    fig.update_layout(title="Illustrative waste history and next 3 months (demo data)")
    st.plotly_chart(style(fig, 300), width="stretch")
    st.caption("The history and forecast are generated demo data. They are not linked to the batches on the other pages. Forecasts never create credits.")
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
        sc = pd.DataFrame({"Scenario": ["Low", "Base", "High", "Stress"], "m": [0.8, 1.0, 1.4, 2.0]})
        sc["Cost to cover the gap"] = max(gap, 0) * price * sc.m
        st.plotly_chart(style(px.bar(sc, x="Scenario", y="Cost to cover the gap", color="Scenario",
                                     color_discrete_sequence=[COL["Dry"], COL["PET"], COL["warn"], COL["fail"]]), 250), width="stretch")
        st.caption("Stress = a sharp price rise before a compliance deadline.")

PAGES = {"Log a collection": page_log, "Log land practice": page_land, "Returned records": page_returned,
         "My parcels": page_parcels, "Confirm practice": page_confirm,
         "Site map": page_map, "Overview": page_overview, "Review queue": page_queue,
         "Post credits": page_post, "Batch trail": page_trail, "Ledger": page_ledger, "Verify credits": page_verify,
         "Retire credits": page_retire, "Insights": page_insights}

# ---------------- main ----------------
st.markdown('<div class="hero">Waste to Credit Studio</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub">{client} · {role}: {ROLES[role][0]}</div>', unsafe_allow_html=True)
opts = ROLES[role][1]
page = st.segmented_control("Page", opts, default=opts[0], key=f"nav_{role}", label_visibility="collapsed") or opts[0]
PAGES[page]()
