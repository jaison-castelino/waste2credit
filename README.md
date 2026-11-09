# Waste to Credit Studio

A small proof of concept (POC) for a waste management and credit allocation service.
It shows how kilograms of waste collected from a client turn into checked, verified credits, and how those credits are used.

> All client names, partners, locations, numbers and conversion factors are **demo placeholders**. They are not real data or official values.

## The idea

This is a **service model**. The software provider collects, enters and processes waste data on behalf of client organisations. The client reviews the results and decides how to use the credits.

Each batch of waste follows this path:

`Collected -> Entered -> Checked (G2, G3, G4) -> Posted (G5) -> Verified (G6) -> Retired`

A **gate** (G2 to G7) is a checkpoint a batch must pass before it moves on.

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
| Data Collection Team | Log a collection, Site map | Enter weights and a receipt, see the credits, submit the batch |
| Platform Admin | Overview, Review queue, Post credits, Batch trail, Site map | Clear or reject flagged batches, post approved credits |
| Verifier | Verify credits, Batch trail | Sign off posted credits |
| Client ESG Manager | Overview, Retire credits, Insights | Retire verified credits against the target, check the forecast |
| Finance / Management | Overview, Insights | See results and price the gap |

## Try this demo path

1. As **Data Collection Team**, open "Log a collection". Open "Try a fraud case" and switch on "Collected away from the site". Click **Submit batch**.
2. As **Platform Admin**, open "Review queue" and click **Clear flags**.
3. Still as Platform Admin, open "Post credits" and click **Approve and post all (G5)**.
4. As **Verifier**, click **Sign off these credits (G6)**.
5. As **Client ESG Manager**, open "Retire credits" and retire the credits.
6. Open "Batch trail" and pick your batch to see its full timeline.

## What the three outputs mean

| Output | Meaning | Counts toward |
|---|---|---|
| Green points | Internal employee rewards (only if the client has a rewards programme) | Nothing official |
| EPR credits | Proof that plastic (PET and HDPE) was recovered | Plastic-recovery targets |
| tCO2e (est.) | Estimated carbon emissions avoided by recycling | ESG and voluntary net-zero goals, once verified |

The conversion rules (points, EPR fraction and CO2e per kg for PET, HDPE and dry waste) can be edited in the sidebar.

## Features

- **Live checks:** gate chips (G2, G3, G4) change as you enter data.
- **Fraud checks:** reused receipt, weight spike, location mismatch, high contamination.
- **Review queue:** flagged batches wait for an admin decision.
- **Site map:** client sites and batch locations. A dot far from its site means the location did not match.
- **Batch trail:** a timeline of every step a batch went through.
- **Overview:** headline tiles, EPR progress gauge, partner performance, and a download of the compliance report (verified credits only).
- **Insights:** a 3-month waste forecast, a credit yield predictor with an audit-loss slider, and a pricing simulator with low, base and high scenarios.

## Known simplifications

- Data lives in memory only. It resets when you reload the page.
- The Verifier stands in for a third-party standards body. A real market would use an independent standards agency.
- The "gap to target" counts all credits earned so far, not only retired ones.
- The plastic share (55%), audit loss and price multipliers are demo assumptions.
- The receipt upload is a demo. The file is not stored or checked.
- Map locations are made-up coordinates.

## Based on

The *Functional Process and Workflow Specification* for the waste management and credit allocation system. Modules and gates in the app follow that document.