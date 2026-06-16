"""
data_fetch.py
==============
Pulls financial statement data (income statement, balance sheet, cash flow)
for an ASX-listed company using yfinance.

Concept (plain English):
- Public companies file financial statements every year (annual report) and
  every quarter/half (interim report). yfinance scrapes these from Yahoo
  Finance and hands them to us as pandas DataFrames.
- The three core statements are:
    1. Income Statement  -> "Did we make money this year?" (Revenue, costs, profit)
    2. Balance Sheet      -> "What do we own and owe, right now?" (Assets, liabilities, equity)
    3. Cash Flow Statement-> "Where did cash actually move?" (Operating, investing, financing)

If yfinance is unreachable (rate limits, network restrictions, etc.), this
module falls back to a small cached snapshot (data/bhp_snapshot.json) built
from BHP's FY2025 Annual Report / ASX announcements, so the rest of the
pipeline (model, DCF, comps, Excel, PDF) can still run end-to-end.
"""

import json
import os
import pandas as pd

TICKER = "BHP.AX"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bhp_snapshot.json")


def fetch_financials_yfinance(ticker: str = TICKER) -> dict:
    """
    Attempt to pull live financial statements via yfinance.

    Returns a dict of pandas DataFrames:
        {"income_stmt": df, "balance_sheet": df, "cash_flow": df, "info": dict}

    Raises an exception if the network call fails (handled by caller).
    """
    import yfinance as yf

    t = yf.Ticker(ticker)
    return {
        "income_stmt": t.income_stmt,
        "balance_sheet": t.balance_sheet,
        "cash_flow": t.cashflow,
        "info": t.info,
    }


def load_cached_snapshot() -> dict:
    """
    Load the cached BHP FY2025 snapshot (sourced from BHP's FY2025 Annual
    Report / ASX & SEC filings, August 2025).

    All figures in US$ millions unless noted, matching how BHP reports
    (BHP's primary financial statements are presented in USD even though
    it trades on the ASX).
    """
    with open(CACHE_PATH, "r") as f:
        return json.load(f)


def get_financials(ticker: str = TICKER, use_cache_if_offline: bool = True) -> dict:
    """
    Main entry point. Tries yfinance first; falls back to cached snapshot.
    """
    try:
        data = fetch_financials_yfinance(ticker)
        # Quick sanity check - yfinance sometimes returns empty frames
        if data["income_stmt"] is None or data["income_stmt"].empty:
            raise ValueError("yfinance returned empty income statement")
        data["source"] = "yfinance (live)"
        return data
    except Exception as e:
        if not use_cache_if_offline:
            raise
        print(f"[data_fetch] yfinance unavailable ({e}). Using cached BHP snapshot.")
        snapshot = load_cached_snapshot()
        snapshot["source"] = "cached snapshot (BHP FY2025 Annual Report)"
        return snapshot


if __name__ == "__main__":
    data = get_financials()
    print("Data source:", data["source"])
    print(json.dumps(data.get("income_statement", data.get("income_stmt", {})), indent=2, default=str)[:1000])
