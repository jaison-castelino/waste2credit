# Waste to Credit Studio

A small proof of concept (POC) for a waste management and credit allocation service.
It shows how waste collected from a client, and farming practice recorded on enrolled land, turn into checked, verified credits, and how those credits are used.

**Live demo: https://waste2credit-jaison-poc.streamlit.app/**

> All client names, partners, farmers, locations, numbers and conversion factors are **demo placeholders**. They are not real data or official values.

## The idea

This is a **service model**. The software provider collects, enters and processes data on behalf of client organisations. The client reviews the results and decides how to use the credits.

Each waste batch or land record follows this path:

`Collected -> Entered -> Checked -> Posted (G5) -> Verified (G6) -> Retired`

A **gate** is a checkpoint a record must pass before it moves on:

| Gate | Question |
|---|---|
| G1 | Is the set-up valid? Waste: are all chain actors registered and licensed? Land: is tenure proven and the boundary free of overlaps? |
| G2 | Is the record complete (receipt, photo, imagery)? |
| C1 to C4 | Waste only. Is the handover reconciled, the transit plausible, the mass balance within tolerance, and the outputs and residue accounted for? |
| G3 | Does the record look genuine? Low risk passes, medium goes to review, high is blocked for investigation. |
| G4 | Are the conversion rules and, for land, an approved methodology available? |
| G5 | Posting approved by the Platform Admin. |
| G6 | Credits signed off by the Verifier. |

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Keep `.streamlit/config.toml` next to `app.py`. It switches on the dark theme.

## Files

| File | What it is |
|---|---|
| `app.py` | The whole app |
| `requirements.txt` | Packages needed (Streamlit 1.50+, Plotly 5.24+, pandas, numpy) |
| `.streamlit/config.toml` | Dark theme colours |

## How to use it

Pick a **client** and a **role** in the sidebar. Each role sees its own pages.

| Role | Pages | What you do |
|---|---|---|
| Data Collection Team | Log a collection, Log land practice, Returned records, Site map | Enter waste batches (with custody checks) and land practice records, close returned records and log corrections |
| Farmer / Landowner | My parcels, Confirm practice | See your parcels and credits, confirm or dispute each practice entry. Farmers do not enter data. |
| Platform Admin | Overview, Review queue, Post credits, Batch trail, Ledger, Site map | Clear, reject or escalate flagged records (a reason is required), post approved credits, reverse land credits, edit the conversion rules |
| Verifier | Verify credits, Batch trail, Ledger | Sign off posted credits |
| Client ESG Manager | Overview, Retire credits, Insights, Ledger | Retire verified credits against the target, check the forecast |
| Finance / Management | Overview, Insights | See results and price the gap |

## Try these demo paths

**Waste, with a fraud flag**

1. As **Data Collection Team**, open "Log a collection". Open "Try a fraud case" and switch on "Collected away from the site". Click **Submit batch**.
2. As **Platform Admin**, open "Review queue", type a reason and click **Clear flags**.
3. Still as Platform Admin, open "Post credits" and click **Approve and post all (G5)**.
4. As **Verifier**, click **Sign off these credits (G6)**.
5. As **Client ESG Manager**, open "Retire credits", pick the lots and retire the EPR credits. Retire the carbon estimates separately.
6. Open "Batch trail" to see the batch timeline and its serial numbers, and "Ledger" to see the journal.

**Land**

1. As **Data Collection Team**, open "Log land practice", choose a parcel and an approved practice (for example rice), and click **Submit practice record**.
2. As **Farmer / Landowner**, open "Confirm practice" (pick the same farmer) and click **Confirm**.
3. Continue from step 3 above: post, verify, then retire. Soil carbon has no approved methodology, so a record for it stays pending at G4.

**Try to break it**

- Submit the same receipt number twice, or the same parcel, practice and season twice. The second one is flagged as a duplicate and blocked.
- Switch on "A chain actor is not registered or licensed". The batch is rejected at G1.
- Raise the land area above the land record. Credits are only calculated on the area in the record.

## What the three outputs mean

| Output | Meaning | Counts toward |
|---|---|---|
| Green points | Internal employee rewards (only if the client has a rewards programme) | Nothing official |
| EPR credits | Proof that plastic (PET and HDPE) was recovered | Plastic-recovery targets |
| tCO2e (est.) | Waste: an indicative estimate only. Land: a calculated figure from an approved methodology, with leakage and buffer taken off | ESG and voluntary net-zero goals, once verified |

For PET, HDPE and dry waste, gate G4 does **not** issue a carbon credit, because no approved methodology applies. EPR credits and carbon estimates are recorded and retired separately, each with its own serial number, so one tonne is never claimed twice.

The conversion rules (points, EPR fraction and CO2e per kg for PET, HDPE, dry waste, e-waste and organic waste) can be edited in the sidebar by the Platform Admin. Every change creates a new dated rule set, and each batch keeps the version it was calculated with. E-waste and organic waste have no approved factor, so those batches stay pending at G4 until one is set and the batch is re-run.

## Waste streams

| Stream | Counted as | Notes |
|---|---|---|
| Plastic and dry waste | Weight (kg) by PET, HDPE, dry waste | Dry waste means clean, dry recyclables other than PET and HDPE, such as other plastics, paper, cardboard, metal and glass |
| E-waste | Units by category, and weight | Only authorised recyclers may process it |
| Organic waste | Weight (kg) | The chain steps are not defined yet |

## Features

- **Live checks:** gate chips (G1 to G4 and C1 to C4) change as you enter data.
- **Chain of custody:** each lot gets a unique ID, with handover, transit, mass-balance and output checks.
- **Fraud checks:** reused receipt, weight spike against site history, vehicle capacity, location mismatch, partner linked to the collection team or client site (self-dealing), repeated round-number weights, unusual PET share, high contamination, missing parent lot. For land: area above the land record, duplicate parcel and season, imagery or fertiliser purchases that contradict the practice log, bulk entries, same land claimed elsewhere.
- **Review queue:** flagged records wait for an admin decision. Every decision needs a reason, and High-risk records are blocked rather than reviewed.
- **Land records:** parcels, practice log, farmer confirmation, and credits calculated as area x factor x (1 - leakage) x (1 - buffer), with a higher buffer for trees and soil.
- **Ledger:** an append-only journal of every status change, with a downloadable statement and a rule-set history.
- **Site map:** client sites, parcels and record locations. A dot far from its site means the location did not match.
- **Batch trail:** a timeline of every step a record went through.
- **Overview:** headline tiles, EPR progress gauge, partner performance, credit funnel, category mix, site leaderboard, land coverage, and a download of the compliance report (verified credits only).
- **Insights:** a 3-month waste forecast, a credit yield predictor with an audit-loss slider, and a pricing simulator with low, base, high and stress scenarios.

## Known simplifications

- Data lives in memory only. It resets when you reload the page.
- Roles and farmers are picked from a dropdown. There is no sign-in.
- The Verifier stands in for a third-party standards body. A real market would use an independent standards agency.
- The "gap to target" counts all credits earned so far, not only retired ones.
- The plastic share (55%), audit loss and price multipliers are demo assumptions.
- The Insights history and forecast are generated demo data. They are not linked to the batches on the other pages.
- Land factors, leakage and buffers are placeholders. The manure methodology is not defined per hectare in reality.
- Duplicate checks use the receipt number and the parcel, practice and season. They do not read the uploaded file or check real boundaries.
- Time-consistency and some self-dealing checks are simulated with toggles.
- The receipt upload is a demo. The file is not stored or checked.
- Rewards wallets and a recycling-rate tile are not built.
- Map locations are made-up coordinates.

## Based on

The *Functional Process and Workflow Specification* for the waste management and credit allocation system. Modules and gates in the app follow that document.
