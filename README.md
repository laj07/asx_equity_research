# BHP Group - ASX Equity Research Model

A self-contained equity research project built in Python, covering BHP Group Limited (ASX: BHP) which is the world's largest diversified mining company. This project demonstrates the core quantitative skills used by junior analysts in investment banking and equity research: financial statement modelling, DCF valuation, and comparable company analysis.

> **Note:** This is a student portfolio project for educational purposes. It does not constitute investment advice.

---

## What This Project Builds

| Output | Description |
|--------|-------------|
| `output/BHP_Equity_Research_Model.xlsx` | 5-tab Excel workbook: Dashboard, 3-Statement Model, Assumptions, DCF, Comps |
| `output/BHP_Investment_Memo.pdf` | 1-page investment memo with recommendation, financials, valuation, sensitivity table |

---

## Project Structure

```
asx_equity_research/
├── data/
│   └── bhp_snapshot.json        # Cached FY2025 actuals (BHP Annual Report / SEC 6-K)
├── src/
│   ├── data_fetch.py            # yfinance pull + cached fallback
│   ├── three_statement_model.py # 3-statement model (IS + BS + CFS, linked)
│   ├── valuation.py             # DCF (WACC/Gordon Growth) + Comps (EV/EBITDA, P/E)
│   ├── build_excel.py           # openpyxl Excel workbook builder
│   └── build_memo.py            # reportlab PDF memo builder
├── notebooks/
│   └── BHP_Analysis.ipynb       # Jupyter notebook walkthrough
├── output/                      # Generated files (not committed)
├── run.py                       # Single entry point — regenerates all outputs
├── requirements.txt
└── README.md
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/asx-equity-research.git
cd asx-equity-research

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python run.py
```

Outputs land in `output/`. On a machine with internet access, `data_fetch.py` pulls live data from Yahoo Finance via `yfinance` (ticker: `BHP.AX`). If that fails (network restriction, rate limit), it falls back to the cached FY2025 snapshot automatically.

---

## Finance Concepts (in Plain English)

### The Three Financial Statements

Every public company files three core statements. This model links all three so that changing one assumption flows through automatically.

| Statement | Question it answers | Key lines |
|-----------|---------------------|-----------|
| **Income Statement** | Did we make money this year? | Revenue → EBITDA → Net Income |
| **Balance Sheet** | What do we own and owe, right now? | Assets = Liabilities + Equity |
| **Cash Flow Statement** | Where did cash actually move? | Operating CF → FCF = CFO − Capex |

**The key links between them:**
- Net Income flows into Retained Earnings (Balance Sheet equity) and is the starting point of the Cash Flow Statement
- Depreciation is a non-cash expense: subtracted on the Income Statement, added back on the Cash Flow Statement
- Capex reduces cash (Cash Flow — Investing) and increases PP&E on the Balance Sheet
- Ending cash from the Cash Flow Statement = Cash on the Balance Sheet

### DCF (Discounted Cash Flow)

> "A company is worth the sum of all the cash it will ever produce, discounted back to today."

Money in the future is worth less than money today — if you had $100 now, you could invest it and have more in 5 years. We use the **WACC** (see below) as the discount rate.

**Steps:**
1. Forecast **Free Cash Flow** (FCF = Operating CF − Capex) for 5 years
2. Discount each year's FCF to **Present Value**: `PV = FCF / (1 + WACC)^n`
3. Estimate a **Terminal Value** (Gordon Growth): `TV = FCF_yr5 × (1+g) / (WACC − g)`
4. `Enterprise Value = Σ PV(FCFs) + PV(Terminal Value)`
5. `Equity Value = Enterprise Value − Net Debt`
6. `Fair Value per Share = Equity Value / Shares Outstanding`

### WACC (Weighted Average Cost of Capital)

The blended "hurdle rate" is 
what investors (debt + equity) require as a return.

```
WACC = (E/V × Cost of Equity) + (D/V × Cost of Debt × (1 − Tax Rate))
Cost of Equity = Risk-Free Rate + Beta × Equity Risk Premium  [CAPM]
```

- **Risk-Free Rate:** ~10yr Australian Government Bond yield (~4.3%)
- **Beta:** BHP's sensitivity to the overall market (~1.05 — slightly cyclical)
- **ERP:** Equity Risk Premium (~5.5% — extra return equities offer over bonds)
- **Tax shield:** Interest payments are tax-deductible, so the effective cost of debt is reduced

### Comparable Company Analysis (Comps)

> "Similar companies should trade at similar multiples."

Two multiples are used:

| Multiple | Formula | What it measures |
|----------|---------|-----------------|
| **EV/EBITDA** | Enterprise Value ÷ EBITDA | Years of operating profit to "buy" the whole company; ignores capital structure differences |
| **P/E** | Share Price ÷ EPS | What investors pay per dollar of after-tax profit |

**Method:** Calculate the peer average/median multiple → apply it to BHP's own EBITDA/EPS → derive an implied share price.

### Why BHP and not a bank?

DCF and EV/EBITDA don't work for banks — their "cost of goods" is interest expense (money is their raw material), so EBITDA is meaningless. Banks are valued using **P/B (Price-to-Book)**, **P/E**, and **DDM (Dividend Discount Model)** instead. BHP's straightforward cash-generative mining business is ideal for teaching these standard frameworks.

---

## Excel Workbook — Color Coding

The Excel model follows industry-standard color conventions:

| Color | Meaning |
|-------|---------|
| 🔵 **Blue text** | Hardcoded inputs — change these to flex the model |
| ⚫ **Black text** | Formulas calculated from inputs |
| 🟢 **Green text** | Links pulling from source data / other sheets |

---

## Data Sources

| Data | Source |
|------|--------|
| FY2025 Revenue, EBITDA, Net Income, Total Assets | BHP FY2025 Annual Report; SEC Form 6-K (19 Aug 2025) |
| Net Debt, Operating Cash Flow, Capex | BHP FY2025 Full Year Results (bhp.com, Aug 2025) |
| Shares Outstanding, Market Cap | Company disclosures; market data |
| Peer multiples (EV/EBITDA, P/E) | Illustrative analyst estimates (mid-2026) for Rio Tinto, Fortescue, Vale, Glencore, South32 |
| Live data (when online) | Yahoo Finance via `yfinance` |

---

## Assumptions & Limitations

- Revenue growth modelled at 2–3% p.a. — conservative for a mature large-cap miner in a stable commodity price environment
- EBITDA margin tapers from FY25's 51% toward BHP's 20-year average of ~50%
- Capex held elevated at ~17% of revenue to reflect BHP's stated FY26–27 capex guidance (~US$11bn/yr) for the Jansen potash project
- Cash flow forecast is simplified: ignores working capital movements, JV distributions and divestment proceeds
- Peer multiples are illustrative estimates for educational purposes — a real research report would source these from Bloomberg/FactSet
- The DCF result is highly sensitive to WACC and terminal growth rate assumptions (see sensitivity table in the PDF memo)

---

## Skills Demonstrated

- **Python:** `yfinance`, `pandas`, `openpyxl`, `reportlab`, modular project structure
- **Financial modelling:** 3-statement model with linked statements, driver-based forecasting
- **Valuation:** DCF (CAPM WACC, Gordon Growth TV), Comparable Company Analysis (EV/EBITDA, P/E)
- **Data sourcing:** Annual reports, SEC EDGAR filings, live market data APIs
- **Excel:** Formula-driven workbook with industry color coding, multi-tab layout
- **Communication:** 1-page investment memo format used in real equity research

---

## Author

Built as a finance portfolio project targeting investment banking / equity research internship applications.  
RMIT University × BITS Pilani | Software Engineering + IT
