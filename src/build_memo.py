"""
build_memo.py
==============
Generates a 1-page PDF investment memo summarising:
  - Company overview
  - Key financials (snapshot of the 3-statement model)
  - Valuation (DCF + Comps)
  - Buy / Hold / Sell recommendation

PLAIN-ENGLISH CONCEPT
---------------------
An "investment memo" (or "research note") is the document an equity
research analyst circulates to portfolio managers. It distills a much
larger model into ~1 page: what the company does, how it's performing,
what it's worth, and what to do about it (buy/hold/sell) - with a brief
rationale that a busy PM can read in 2 minutes.
"""

import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

sys.path.insert(0, os.path.dirname(__file__))
import data_fetch
import three_statement_model as tsm
import valuation as val
from build_excel import derive_recommendation

NAVY = HexColor("#1F4E78")
GREY = HexColor("#595959")
GREEN = HexColor("#2E7D32")
AMBER = HexColor("#F9A825")
RED = HexColor("#C62828")
LIGHT_GREY = HexColor("#F2F2F2")


def build_memo(snapshot, model, dcf, comps, out_path):
    company = snapshot["company"]
    rec, rationale, blended = derive_recommendation(dcf, comps)
    rec_color = {"BUY": GREEN, "HOLD": AMBER, "SELL": RED}[rec]

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18,
                                  textColor=NAVY, spaceAfter=2, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8.5,
                                textColor=GREY, spaceAfter=6, fontName="Helvetica-Oblique")
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11,
                               textColor=NAVY, spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold")
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8.5,
                                 leading=11.5, fontName="Helvetica")
    disclaimer_style = ParagraphStyle("Disc", parent=styles["Normal"], fontSize=6.5,
                                       textColor=GREY, fontName="Helvetica-Oblique", leading=8)

    elements = []

    # --- Header ---
    elements.append(Paragraph(f"{company['name']} ({company['ticker']}) — Equity Research Note", title_style))
    elements.append(Paragraph(
        f"Sector: {company['sector']} | Industry: {company['industry']} | "
        f"Date: 15 June 2026 | Analyst: Equity Research (Student Portfolio Project)", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=6))

    # --- Recommendation banner ---
    rec_table = Table(
        [[Paragraph(f"<b>RECOMMENDATION: {rec}</b>", ParagraphStyle(
            "RecBig", fontSize=13, textColor=HexColor("#FFFFFF"), fontName="Helvetica-Bold", alignment=TA_LEFT)),
          Paragraph(
              f"Current Price: A${dcf['current_share_price_aud']:.2f} &nbsp;|&nbsp; "
              f"DCF Fair Value: A${dcf['implied_share_price_aud']:.2f} "
              f"({dcf['upside_downside_pct']:+.1%}) &nbsp;|&nbsp; "
              f"Comps Implied: A${(comps['implied_price_ev_avg_aud'] + comps['implied_price_pe_avg_aud'])/2:.2f}",
              ParagraphStyle("RecDetail", fontSize=9, textColor=HexColor("#FFFFFF"), fontName="Helvetica",
                             alignment=TA_LEFT))]],
        colWidths=[165, 325])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rec_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(rec_table)
    elements.append(Spacer(1, 6))

    # --- Company Overview ---
    elements.append(Paragraph("Company Overview", h2_style))
    elements.append(Paragraph(company["description"], body_style))
    elements.append(Spacer(1, 4))

    # --- Two-column layout: Key Financials | Valuation ---
    inc = model["income_statement"]
    bs = model["balance_sheet"]
    cf = model["cash_flow"]

    fin_data = [
        ["Key Financials (USDm)", "FY24A", "FY25A", "FY26E", "FY30E"],
        ["Revenue", f"{inc.loc['Revenue','FY24A']:,.0f}", f"{inc.loc['Revenue','FY25A']:,.0f}",
         f"{inc.loc['Revenue','FY26E']:,.0f}", f"{inc.loc['Revenue','FY30E']:,.0f}"],
        ["EBITDA", f"{inc.loc['EBITDA','FY24A']:,.0f}", f"{inc.loc['EBITDA','FY25A']:,.0f}",
         f"{inc.loc['EBITDA','FY26E']:,.0f}", f"{inc.loc['EBITDA','FY30E']:,.0f}"],
        ["EBITDA Margin", f"{inc.loc['EBITDA','FY24A']/inc.loc['Revenue','FY24A']:.1%}",
         f"{inc.loc['EBITDA','FY25A']/inc.loc['Revenue','FY25A']:.1%}",
         f"{inc.loc['EBITDA','FY26E']/inc.loc['Revenue','FY26E']:.1%}",
         f"{inc.loc['EBITDA','FY30E']/inc.loc['Revenue','FY30E']:.1%}"],
        ["Net Income", f"{inc.loc['Net Income','FY24A']:,.0f}", f"{inc.loc['Net Income','FY25A']:,.0f}",
         f"{inc.loc['Net Income','FY26E']:,.0f}", f"{inc.loc['Net Income','FY30E']:,.0f}"],
        ["Free Cash Flow", f"{cf.loc['Free Cash Flow','FY24A']:,.0f}", f"{cf.loc['Free Cash Flow','FY25A']:,.0f}",
         f"{cf.loc['Free Cash Flow','FY26E']:,.0f}", f"{cf.loc['Free Cash Flow','FY30E']:,.0f}"],
        ["Net Debt", f"{bs.loc['Net Debt','FY24A']:,.0f}", f"{bs.loc['Net Debt','FY25A']:,.0f}",
         f"{bs.loc['Net Debt','FY26E']:,.0f}", f"{bs.loc['Net Debt','FY30E']:,.0f}"],
    ]

    val_data = [
        ["Valuation Summary", "Value"],
        ["WACC", f"{dcf['wacc']:.2%}"],
        ["Terminal Growth Rate", f"{dcf['terminal_growth_rate']:.1%}"],
        ["Enterprise Value (USDm)", f"{dcf['enterprise_value']:,.0f}"],
        ["Equity Value (USDm)", f"{dcf['equity_value']:,.0f}"],
        ["DCF Fair Value (AUD)", f"A${dcf['implied_share_price_aud']:.2f}"],
        ["EV/EBITDA Comps (AUD)", f"A${comps['implied_price_ev_avg_aud']:.2f}"],
        ["P/E Comps (AUD)", f"A${comps['implied_price_pe_avg_aud']:.2f}"],
        ["BHP EV/EBITDA (current)", f"{comps['bhp_current_ev_ebitda']:.1f}x"],
        ["Peer Avg EV/EBITDA", f"{comps['peer_avg_ev_ebitda']:.1f}x"],
    ]

    fin_table = Table(fin_data, colWidths=[78, 38, 38, 38, 38])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    val_table = Table(val_data, colWidths=[110, 60])
    val_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    combined = Table([[fin_table, val_table]], colWidths=[235, 175])
    combined.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(Paragraph("Key Financials &amp; Valuation Summary", h2_style))
    elements.append(combined)
    elements.append(Spacer(1, 6))

    # --- Investment Thesis / Rationale ---
    elements.append(Paragraph("Investment Thesis", h2_style))
    elements.append(Paragraph(rationale, body_style))
    elements.append(Spacer(1, 3))

    bull_bear = [
        ["Bull Case", "Bear Case"],
        [Paragraph("World's lowest-cost major iron ore producer, providing earnings resilience through "
                    "commodity cycles. Growing copper exposure (~45% of EBITDA) positions BHP toward "
                    "structural decarbonisation/electrification demand. Strong balance sheet (net debt "
                    "well within target range) supports continued shareholder returns.", body_style),
         Paragraph("Trades at a meaningful premium to peer multiples and DCF fair value, leaving limited "
                    "margin of safety if commodity prices soften. Elevated capex (Jansen potash project) "
                    "weighs on near-term free cash flow and dividend coverage. Earnings remain highly "
                    "sensitive to iron ore and copper price swings outside management's control.", body_style)],
    ]
    bb_table = Table(bull_bear, colWidths=[205, 205])
    bb_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(bb_table)
    elements.append(Spacer(1, 8))

    # --- Sensitivity Table (WACC vs Terminal Growth) ---
    elements.append(Paragraph("DCF Sensitivity — Implied Share Price (AUD)", h2_style))
    wacc_base = dcf["wacc"]
    g_base = dcf["terminal_growth_rate"]
    wacc_range = [wacc_base - 0.01, wacc_base - 0.005, wacc_base, wacc_base + 0.005, wacc_base + 0.01]
    g_range = [g_base - 0.005, g_base, g_base + 0.005]

    sens_header = ["WACC \\ Terminal g"] + [f"{g:.1%}" for g in g_range]
    sens_rows = [sens_header]
    fcf_forecast = model["cash_flow"].loc["Free Cash Flow"]
    forecast_years_list = [c for c in fcf_forecast.index if c.endswith("E")]
    net_debt_val = dcf["net_debt"]
    shares_m = snapshot["company"]["shares_outstanding_m"]
    fx = snapshot["company"]["aud_usd_fx"]

    for w in wacc_range:
        row = [f"{w:.2%}"]
        for g in g_range:
            pv_sum = sum(fcf_forecast[y] / ((1 + w) ** (i + 1)) for i, y in enumerate(forecast_years_list))
            tv = fcf_forecast[forecast_years_list[-1]] * (1 + g) / (w - g)
            pv_tv = tv / ((1 + w) ** len(forecast_years_list))
            ev = pv_sum + pv_tv
            eq = ev - net_debt_val
            price_aud = (eq / shares_m) / fx
            row.append(f"A${price_aud:.2f}")
        sens_rows.append(row)

    sens_table = Table(sens_rows, colWidths=[80] + [82] * 3)
    sens_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("BACKGROUND", (0, 1), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 1), (0, -1), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [HexColor("#FFFFFF"), LIGHT_GREY]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Highlight base case cell
    base_row_idx = wacc_range.index(wacc_base) + 1
    base_col_idx = g_range.index(g_base) + 1
    sens_style.append(("BACKGROUND", (base_col_idx, base_row_idx), (base_col_idx, base_row_idx), HexColor("#D9E1F2")))
    sens_style.append(("BOX", (base_col_idx, base_row_idx), (base_col_idx, base_row_idx), 1, NAVY))
    sens_table.setStyle(TableStyle(sens_style))
    elements.append(sens_table)
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "Highlighted cell = base case assumptions. Fair value is most sensitive to the WACC assumption; "
        "a 1pp WACC decrease lifts implied value materially due to the long-duration terminal value component.",
        ParagraphStyle("SensNote", parent=body_style, fontSize=7.5, textColor=GREY)))
    elements.append(Spacer(1, 8))

    # --- Methodology Summary ---
    elements.append(Paragraph("Methodology Summary", h2_style))
    elements.append(Paragraph(
        "<b>3-Statement Model:</b> FY24A-FY25A actuals from BHP's FY2025 Annual Report, projected FY26E-FY30E "
        "using driver-based assumptions (revenue growth, EBITDA margin, D&amp;A and capex as % of revenue). "
        "<b>DCF:</b> 5-year explicit FCF forecast discounted at WACC (CAPM-derived cost of equity + after-tax "
        "cost of debt), plus a Gordon Growth terminal value. <b>Comps:</b> EV/EBITDA and P/E multiples from a "
        "5-company diversified mining peer set applied to BHP's FY25 EBITDA and EPS. Full assumptions, "
        "formulas and source citations are documented in the accompanying Excel model and GitHub README.",
        body_style))
    elements.append(Spacer(1, 6))

    # --- Disclaimer ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY, spaceAfter=3))
    elements.append(Paragraph(
        "Disclaimer: This document is a student portfolio project produced for educational purposes only. "
        "It does not constitute investment advice, a research report under applicable securities regulations, "
        "or a recommendation to buy or sell any security. Historical financial figures are sourced from BHP "
        "Group's FY2025 Annual Report and SEC Form 6-K filings (August 2025); forecasts and peer multiples "
        "are illustrative estimates built using simplified modeling assumptions documented in the accompanying "
        "GitHub repository. Past performance is not indicative of future results.", disclaimer_style))

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                             leftMargin=16 * mm, rightMargin=16 * mm,
                             topMargin=10 * mm, bottomMargin=10 * mm)
    doc.build(elements)
    print(f"Saved: {out_path}")


def main():
    snapshot = data_fetch.get_financials()
    model = tsm.build_model(snapshot)
    dcf = val.run_dcf(model, snapshot)
    comps = val.run_comps(model, snapshot)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "BHP_Investment_Memo.pdf")
    build_memo(snapshot, model, dcf, comps, out_path)


if __name__ == "__main__":
    main()
