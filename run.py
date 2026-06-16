"""
run.py
-------
Single entry point. Run this to regenerate all outputs:
  - output/BHP_Equity_Research_Model.xlsx
  - output/BHP_Investment_Memo.pdf

Usage:
    python run.py

On first run it will attempt to pull live data from Yahoo Finance
via yfinance (BHP.AX). If the network call fails it falls back to
the cached snapshot in data/bhp_snapshot.json (BHP FY2025 actuals
sourced from the Annual Report / SEC Form 6-K, August 2025).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import data_fetch
import three_statement_model as tsm
import valuation as val
from build_excel import main as build_excel
from build_memo import build_memo

if __name__ == "__main__":
    print("=" * 55)
    print("  BHP Group — Equity Research Model")
    print("  ASX: BHP.AX | FY2025 actuals + 5-year forecast")
    print("=" * 55)

    print("\n[1/4] Fetching financial data...")
    snapshot = data_fetch.get_financials()
    print(f"      Source: {snapshot['source']}")

    print("[2/4] Building 3-statement model...")
    model = tsm.build_model(snapshot)

    print("[3/4] Running DCF + Comps valuation...")
    dcf = val.run_dcf(model, snapshot)
    comps = val.run_comps(model, snapshot)
    print(f"      DCF implied: A${dcf['implied_share_price_aud']:.2f} "
          f"({dcf['upside_downside_pct']:+.1%} vs current A${dcf['current_share_price_aud']:.2f})")
    print(f"      EV/EBITDA comps implied: A${comps['implied_price_ev_avg_aud']:.2f}")

    print("[4/4] Generating Excel model + PDF memo...")
    os.makedirs("output", exist_ok=True)
    _, _, _, _, _ = build_excel()

    memo_path = os.path.join("output", "BHP_Investment_Memo.pdf")
    build_memo(snapshot, model, dcf, comps, memo_path)

    print("\nDone. Outputs written to /output:")
    print("  - BHP_Equity_Research_Model.xlsx")
    print("  - BHP_Investment_Memo.pdf")
