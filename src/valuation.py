"""
valuation.py
=============
Two valuation methods:
  1. DCF (Discounted Cash Flow) - intrinsic value based on BHP's own
     projected cash flows.
  2. Comparable Company Analysis ("Comps") - relative value, based on
     how the market prices similar mining companies (EV/EBITDA, P/E).

PLAIN-ENGLISH CONCEPTS
----------------------

DCF (Discounted Cash Flow)
  Idea: "A company is worth the sum of all the cash it will ever produce
  for its owners, but cash in the future is worth less than cash today."

  Why? If I gave you $100 today vs. $100 in 5 years, you'd take it today -
  you could invest it and have MORE than $100 in 5 years. So future cash
  flows get "discounted" (shrunk) back to today's value using a discount
  rate. We use WACC (Weighted Average Cost of Capital) as that rate.

  Steps:
    1. Forecast Free Cash Flow (FCF) for 5 years (from the 3-statement model)
    2. Discount each year's FCF back to present value using WACC
    3. Estimate a "Terminal Value" - the value of all cash flows AFTER
       year 5, assuming the company grows at a stable rate forever
       (Gordon Growth Model): TV = FCF_yr5 * (1+g) / (WACC - g)
    4. Sum discounted FCFs + discounted Terminal Value = Enterprise Value
    5. Enterprise Value - Net Debt = Equity Value
    6. Equity Value / Shares Outstanding = Fair Value per Share

WACC (Weighted Average Cost of Capital)
  The "hurdle rate" - blended cost of a company's debt and equity funding.
  WACC = (E/V * Cost of Equity) + (D/V * Cost of Debt * (1 - Tax Rate))
  where E = equity value, D = debt value, V = E + D.
  - Cost of Equity is usually estimated via CAPM:
        Cost of Equity = Risk-Free Rate + Beta * Equity Risk Premium
  - Cost of Debt * (1 - Tax) reflects that interest payments are
    tax-deductible (the "tax shield").

Comparable Company Analysis ("Comps")
  Idea: "Similar companies should trade at similar multiples."
  - EV/EBITDA = Enterprise Value / EBITDA
      Tells you how many years of operating profit (before financing
      and accounting decisions) it would take to buy the whole company.
      Useful because it ignores differences in debt levels and tax rates
      between companies - good for comparing miners with different
      capital structures.
  - P/E = Share Price / Earnings per Share
      How much investors pay for each dollar of (after-tax, after-debt)
      profit. Sensitive to debt levels and one-off items.
  - Method: take peer multiples, apply the AVERAGE/MEDIAN peer multiple
    to BHP's own EBITDA/EPS to get an "implied" valuation.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# DCF
# ---------------------------------------------------------------------------
WACC_ASSUMPTIONS = {
    "risk_free_rate": 0.043,     # ~10yr Australian Govt Bond yield
    "beta": 1.05,                 # BHP beta (commodity-cyclical, slightly above market)
    "equity_risk_premium": 0.055,
    "cost_of_debt": 0.052,        # BHP's blended borrowing rate
    "tax_rate": 0.30,             # Australian corporate tax rate
    "terminal_growth_rate": 0.025,  # ~long-run nominal GDP growth proxy
}


def calc_wacc(market_cap_usd_m: float, total_debt_usd_m: float, assumptions: dict = None) -> dict:
    """
    Calculate WACC using CAPM for cost of equity.
    """
    a = assumptions or WACC_ASSUMPTIONS
    cost_of_equity = a["risk_free_rate"] + a["beta"] * a["equity_risk_premium"]
    cost_of_debt_after_tax = a["cost_of_debt"] * (1 - a["tax_rate"])

    total_value = market_cap_usd_m + total_debt_usd_m
    weight_equity = market_cap_usd_m / total_value
    weight_debt = total_debt_usd_m / total_value

    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt_after_tax)

    return {
        "cost_of_equity": cost_of_equity,
        "cost_of_debt_after_tax": cost_of_debt_after_tax,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
        "wacc": wacc,
    }


def run_dcf(model: dict, snapshot: dict, wacc_assumptions: dict = None) -> dict:
    """
    Run a 5-year DCF using FCF from the 3-statement model.

    Returns a dict with the per-year discounted FCFs, terminal value,
    enterprise value, equity value, and implied share price.
    """
    a = wacc_assumptions or WACC_ASSUMPTIONS
    company = snapshot["company"]

    market_cap_usd_m = company["market_cap_aud_m"] * company["aud_usd_fx"]
    total_debt_usd_m = snapshot["balance_sheet"]["fy"]["2025"]["total_debt"]

    wacc_result = calc_wacc(market_cap_usd_m, total_debt_usd_m, a)
    wacc = wacc_result["wacc"]
    g = a["terminal_growth_rate"]

    fcf_forecast = model["cash_flow"].loc["Free Cash Flow"]
    forecast_years = [c for c in fcf_forecast.index if c.endswith("E")]

    pv_fcfs = {}
    for i, year in enumerate(forecast_years, start=1):
        fcf = fcf_forecast[year]
        discount_factor = 1 / ((1 + wacc) ** i)
        pv_fcfs[year] = fcf * discount_factor

    # Terminal value (Gordon Growth), discounted back from end of year 5
    final_year_fcf = fcf_forecast[forecast_years[-1]]
    terminal_value = final_year_fcf * (1 + g) / (wacc - g)
    pv_terminal_value = terminal_value / ((1 + wacc) ** len(forecast_years))

    enterprise_value = sum(pv_fcfs.values()) + pv_terminal_value

    net_debt = snapshot["balance_sheet"]["fy"]["2025"]["net_debt"]
    equity_value = enterprise_value - net_debt

    shares_outstanding_m = company["shares_outstanding_m"]
    implied_share_price_usd = equity_value / shares_outstanding_m
    implied_share_price_aud = implied_share_price_usd / company["aud_usd_fx"]

    return {
        "wacc_breakdown": wacc_result,
        "wacc": wacc,
        "terminal_growth_rate": g,
        "pv_fcfs": pv_fcfs,
        "sum_pv_fcfs": sum(pv_fcfs.values()),
        "terminal_value_undiscounted": terminal_value,
        "pv_terminal_value": pv_terminal_value,
        "enterprise_value": enterprise_value,
        "net_debt": net_debt,
        "equity_value": equity_value,
        "implied_share_price_usd": implied_share_price_usd,
        "implied_share_price_aud": implied_share_price_aud,
        "current_share_price_aud": company["share_price_aud"],
        "upside_downside_pct": (implied_share_price_aud / company["share_price_aud"]) - 1,
    }


# ---------------------------------------------------------------------------
# COMPARABLE COMPANY ANALYSIS
# ---------------------------------------------------------------------------
# Peer set: large diversified / iron-ore-heavy ASX & global miners.
# Multiples below are illustrative analyst-style estimates as of mid-2026,
# representative of the ranges these stocks have traded at.
PEER_COMPS = pd.DataFrame({
    "Company": ["Rio Tinto", "Fortescue", "Vale S.A.", "Glencore", "South32"],
    "Ticker": ["RIO.AX", "FMG.AX", "VALE", "GLEN.L", "S32.AX"],
    "EV/EBITDA": [5.2, 4.6, 4.1, 4.8, 5.5],
    "P/E": [10.8, 9.5, 8.2, 11.5, 12.1],
})


def run_comps(model: dict, snapshot: dict, peers: pd.DataFrame = None) -> dict:
    """
    Apply peer average/median multiples to BHP's own EBITDA and EPS.
    """
    peers = peers if peers is not None else PEER_COMPS
    company = snapshot["company"]

    bhp_ebitda_fy25 = model["income_statement"].loc["EBITDA", "FY25A"]
    bhp_net_income_fy25 = model["income_statement"].loc["Net Income", "FY25A"]
    shares_outstanding_m = company["shares_outstanding_m"]
    bhp_eps_usd = bhp_net_income_fy25 / shares_outstanding_m

    avg_ev_ebitda = peers["EV/EBITDA"].mean()
    med_ev_ebitda = peers["EV/EBITDA"].median()
    avg_pe = peers["P/E"].mean()
    med_pe = peers["P/E"].median()

    net_debt = snapshot["balance_sheet"]["fy"]["2025"]["net_debt"]

    # EV/EBITDA implied valuation
    implied_ev_avg = avg_ev_ebitda * bhp_ebitda_fy25
    implied_equity_avg = implied_ev_avg - net_debt
    implied_price_ev_avg_usd = implied_equity_avg / shares_outstanding_m
    implied_price_ev_avg_aud = implied_price_ev_avg_usd / company["aud_usd_fx"]

    implied_ev_med = med_ev_ebitda * bhp_ebitda_fy25
    implied_equity_med = implied_ev_med - net_debt
    implied_price_ev_med_usd = implied_equity_med / shares_outstanding_m
    implied_price_ev_med_aud = implied_price_ev_med_usd / company["aud_usd_fx"]

    # P/E implied valuation
    implied_price_pe_avg_usd = avg_pe * bhp_eps_usd
    implied_price_pe_avg_aud = implied_price_pe_avg_usd / company["aud_usd_fx"]

    implied_price_pe_med_usd = med_pe * bhp_eps_usd
    implied_price_pe_med_aud = implied_price_pe_med_usd / company["aud_usd_fx"]

    # BHP's own current implied multiples (for context)
    bhp_market_cap_usd = company["market_cap_aud_m"] * company["aud_usd_fx"]
    bhp_ev_usd = bhp_market_cap_usd + net_debt
    bhp_current_ev_ebitda = bhp_ev_usd / bhp_ebitda_fy25
    bhp_current_pe = company["share_price_aud"] / (bhp_eps_usd / company["aud_usd_fx"])

    return {
        "peers": peers,
        "peer_avg_ev_ebitda": avg_ev_ebitda,
        "peer_median_ev_ebitda": med_ev_ebitda,
        "peer_avg_pe": avg_pe,
        "peer_median_pe": med_pe,
        "bhp_ebitda_fy25": bhp_ebitda_fy25,
        "bhp_eps_usd": bhp_eps_usd,
        "bhp_current_ev_ebitda": bhp_current_ev_ebitda,
        "bhp_current_pe": bhp_current_pe,
        "implied_price_ev_avg_aud": implied_price_ev_avg_aud,
        "implied_price_ev_med_aud": implied_price_ev_med_aud,
        "implied_price_pe_avg_aud": implied_price_pe_avg_aud,
        "implied_price_pe_med_aud": implied_price_pe_med_aud,
        "current_share_price_aud": company["share_price_aud"],
    }


if __name__ == "__main__":
    import data_fetch
    import three_statement_model as tsm

    snap = data_fetch.get_financials()
    model = tsm.build_model(snap)

    dcf = run_dcf(model, snap)
    print("\n=== DCF VALUATION ===")
    print(f"WACC: {dcf['wacc']:.2%}")
    print(f"Sum of PV of FCFs (USDm): {dcf['sum_pv_fcfs']:,.0f}")
    print(f"PV of Terminal Value (USDm): {dcf['pv_terminal_value']:,.0f}")
    print(f"Enterprise Value (USDm): {dcf['enterprise_value']:,.0f}")
    print(f"Equity Value (USDm): {dcf['equity_value']:,.0f}")
    print(f"Implied Share Price (AUD): ${dcf['implied_share_price_aud']:.2f}")
    print(f"Current Share Price (AUD): ${dcf['current_share_price_aud']:.2f}")
    print(f"Upside/(Downside): {dcf['upside_downside_pct']:.1%}")

    comps = run_comps(model, snap)
    print("\n=== COMPARABLE COMPANY ANALYSIS ===")
    print(comps["peers"])
    print(f"\nPeer avg EV/EBITDA: {comps['peer_avg_ev_ebitda']:.1f}x  -> Implied price: ${comps['implied_price_ev_avg_aud']:.2f}")
    print(f"Peer avg P/E: {comps['peer_avg_pe']:.1f}x  -> Implied price: ${comps['implied_price_pe_avg_aud']:.2f}")
    print(f"BHP current EV/EBITDA: {comps['bhp_current_ev_ebitda']:.1f}x")
    print(f"BHP current P/E: {comps['bhp_current_pe']:.1f}x")
