"""
three_statement_model.py
=========================
Builds a simplified 3-statement financial model for BHP:
  - Income Statement
  - Balance Sheet
  - Cash Flow Statement
...linked together and projected forward 5 years.

PLAIN-ENGLISH CONCEPTS
----------------------
1. The three statements answer different questions:
   - Income Statement: "Did the company make a profit this year?"
   - Balance Sheet: "What does the company own (assets) and owe
     (liabilities), and what's left for shareholders (equity), at a
     single point in time?"
   - Cash Flow Statement: "Where did cash actually come from and go?"
     (Profit on paper != cash in the bank, e.g. depreciation is an
     expense that doesn't involve any cash leaving.)

2. How they connect (the "plumbing"):
   - Net Income (bottom of Income Statement) is the starting point of
     the Cash Flow Statement, AND it flows into Retained Earnings on
     the Balance Sheet (profits accumulate as shareholder wealth).
   - Depreciation is subtracted as an expense on the Income Statement,
     but it's a non-cash charge, so it's ADDED BACK on the Cash Flow
     Statement.
   - Capex (money spent buying equipment/mines/property) reduces cash
     (Cash Flow - Investing) and increases PP&E (Balance Sheet asset).
   - The ending cash balance from the Cash Flow Statement becomes the
     "Cash" line on next year's Balance Sheet.
   - The Balance Sheet must always balance: Assets = Liabilities + Equity.

3. Forecasting approach used here (simplified, "driver-based"):
   - Revenue grows at an assumed annual rate.
   - EBITDA margin is held at a target level (BHP's underlying margin
     has historically been ~50-55%, we taper toward a normalised level).
   - D&A and Capex are modeled as a % of revenue (common shorthand).
   - Net debt is assumed to stay roughly flat (BHP targets a net debt
     range, not zero debt - mining companies use debt to fund growth).
"""

import pandas as pd

# ---------------------------------------------------------------------------
# ASSUMPTIONS (the "drivers" of the forecast)
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    "revenue_growth": [0.02, 0.03, 0.03, 0.025, 0.025],   # Yr1..Yr5, modest growth
    "ebitda_margin": [0.52, 0.51, 0.51, 0.50, 0.50],       # tapering toward long-run avg
    "da_pct_revenue": 0.12,                                 # D&A as % of revenue
    "tax_rate": 0.31,                                       # ~effective rate ex. royalties drag
    "capex_pct_revenue": 0.17,                              # heavy capex cycle (Jansen project etc.)
    "net_debt_target": 13000,                               # USDm, within BHP's stated 10-20bn range
    "shares_outstanding_m": 5382.6,
}

FORECAST_YEARS = ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"]


def build_model(snapshot: dict, assumptions: dict = None) -> dict:
    """
    Build the linked 3-statement model.

    Returns a dict with three pandas DataFrames:
        income_statement, balance_sheet, cash_flow
    Columns = FY24A, FY25A, FY26E..FY30E
    """
    a = assumptions or ASSUMPTIONS
    inc = snapshot["income_statement"]["fy"]
    bal = snapshot["balance_sheet"]["fy"]
    cfs = snapshot["cash_flow_statement"]["fy"]

    # --- Historical base ---
    years = ["FY24A", "FY25A"]
    revenue = {"FY24A": inc["2024"]["revenue"], "FY25A": inc["2025"]["revenue"]}
    ebitda = {"FY24A": inc["2024"]["ebitda"], "FY25A": inc["2025"]["ebitda"]}
    da = {"FY24A": inc["2024"]["depreciation_amortisation"], "FY25A": inc["2025"]["depreciation_amortisation"]}
    net_finance = {"FY24A": inc["2024"]["net_finance_costs"], "FY25A": inc["2025"]["net_finance_costs"]}
    tax = {"FY24A": inc["2024"]["tax_expense"], "FY25A": inc["2025"]["tax_expense"]}
    net_income = {"FY24A": inc["2024"]["profit_after_tax"], "FY25A": inc["2025"]["profit_after_tax"]}

    total_assets = {"FY24A": bal["2024"]["total_assets"], "FY25A": bal["2025"]["total_assets"]}
    total_equity = {"FY24A": bal["2024"]["total_equity"], "FY25A": bal["2025"]["total_equity"]}
    net_debt = {"FY24A": bal["2024"]["net_debt"], "FY25A": bal["2025"]["net_debt"]}
    cash = {"FY24A": bal["2024"]["cash_and_equivalents"], "FY25A": bal["2025"]["cash_and_equivalents"]}

    capex = {"FY24A": cfs["2024"]["capital_and_exploration_expenditure"],
             "FY25A": cfs["2025"]["capital_and_exploration_expenditure"]}
    cfo = {"FY24A": cfs["2024"]["net_operating_cash_flow"], "FY25A": cfs["2025"]["net_operating_cash_flow"]}
    fcf = {"FY24A": cfs["2024"]["free_cash_flow"], "FY25A": cfs["2025"]["free_cash_flow"]}
    dividends = {"FY24A": cfs["2024"]["dividends_paid"], "FY25A": cfs["2025"]["dividends_paid"]}

    # --- Forecast ---
    prev_year = "FY25A"
    for i, fy in enumerate(FORECAST_YEARS):
        years.append(fy)
        # Income statement drivers
        revenue[fy] = revenue[prev_year] * (1 + a["revenue_growth"][i])
        ebitda[fy] = revenue[fy] * a["ebitda_margin"][i]
        da[fy] = revenue[fy] * a["da_pct_revenue"]
        ebit = ebitda[fy] - da[fy]
        net_finance[fy] = net_finance[prev_year]  # hold flat (net debt roughly stable)
        pbt = ebit - net_finance[fy]
        tax[fy] = pbt * a["tax_rate"]
        net_income[fy] = pbt - tax[fy]

        # Cash flow
        capex[fy] = revenue[fy] * a["capex_pct_revenue"]
        # CFO approximated as Net Income + D&A (simplified - ignores working capital swings)
        cfo[fy] = net_income[fy] + da[fy]
        fcf[fy] = cfo[fy] - capex[fy]
        dividends[fy] = net_income[fy] * 0.55  # BHP's ~55% payout ratio

        # Balance sheet roll-forward
        net_debt[fy] = a["net_debt_target"]
        retained_earnings_change = net_income[fy] - dividends[fy]
        total_equity[fy] = total_equity[prev_year] + retained_earnings_change
        cash[fy] = cash[prev_year] + fcf[fy] - dividends[fy] - (net_debt[fy] - net_debt[prev_year])
        # Total assets = Equity + Liabilities; hold liabilities/equity ratio
        # roughly stable for plausibility (simplification)
        total_liabilities_prev_ratio = (total_assets[prev_year] - total_equity[prev_year]) / total_equity[prev_year]
        total_liabilities = total_equity[fy] * total_liabilities_prev_ratio
        total_assets[fy] = total_equity[fy] + total_liabilities

        prev_year = fy

    # --- Assemble DataFrames ---
    income_statement = pd.DataFrame({
        "Revenue": revenue,
        "EBITDA": ebitda,
        "D&A": da,
        "EBIT": {y: ebitda[y] - da[y] for y in years},
        "Net Finance Costs": net_finance,
        "Profit Before Tax": {y: (ebitda[y] - da[y]) - net_finance[y] for y in years},
        "Tax Expense": tax,
        "Net Income": net_income,
    }).T[years]

    balance_sheet = pd.DataFrame({
        "Total Assets": total_assets,
        "Total Equity": total_equity,
        "Net Debt": net_debt,
        "Cash & Equivalents": cash,
    }).T[years]

    cash_flow = pd.DataFrame({
        "Net Operating Cash Flow": cfo,
        "Capex": capex,
        "Free Cash Flow": fcf,
        "Dividends Paid": dividends,
    }).T[years]

    return {
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "assumptions": a,
        "years": years,
    }


if __name__ == "__main__":
    import data_fetch
    snap = data_fetch.get_financials()
    model = build_model(snap)
    pd.set_option("display.float_format", lambda x: f"{x:,.0f}")
    print("\n=== INCOME STATEMENT (USDm) ===")
    print(model["income_statement"])
    print("\n=== BALANCE SHEET (USDm) ===")
    print(model["balance_sheet"])
    print("\n=== CASH FLOW STATEMENT (USDm) ===")
    print(model["cash_flow"])
