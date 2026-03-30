"""
Task 2: Data Analysis and Trading Strategies
==========================================
Analysis of German wind/PV forecasts and power prices for 2021,
plus 3 trading strategies exploiting DA->ID price spreads.

Run:  python task2/analysis.py
      -> saves all plots to task2/plots/
"""

import os
import warnings
import sqlite3

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")

# -- Style ----------------------------------------
BLUE   = "#1f77b4"
ORANGE = "#ff7f0e"
GREEN  = "#2ca02c"
RED    = "#d62728"
PURPLE = "#9467bd"
DARK   = "#2b2b2b"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "#f8f9fa",
    "axes.grid":        True,
    "grid.alpha":       0.4,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "font.size":        11,
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
})

PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)


# -- Data loading ----------------------------------------

def load_data() -> pd.DataFrame:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "analysis_task_data.xlsx")
    df = pd.read_excel(path, sheet_name="DE_Wind_PV_Prices", header=0)
    df = df.rename(columns={
        "Wind Day Ahead Forecast [in MW]":               "wind_da_mw",
        "Wind Intraday Forecast [in MW]":                "wind_id_mw",
        "PV Day Ahead Forecast [in MW]":                 "pv_da_mw",
        "PV Intraday Forecast [in MW]":                  "pv_id_mw",
        "Day Ahead Price hourly [in EUR/MWh]":           "da_price",
        "Intraday Price Price Quarter Hourly  [in EUR/MWh]": "id_price_15",
        "Intraday Price Hourly  [in EUR/MWh]":           "id_price_h",
        "Imbalance Price Quarter Hourly  [in EUR/MWh]":  "imbalance_price",
    })
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df["date"]    = df.index.date
    df["weekday"] = df.index.dayofweek          # 0=Mon … 6=Sun
    df["is_weekend"] = df["weekday"] >= 5
    df["month"]   = df.index.month
    df["season"]  = df["month"].map(
        {12:"Winter",1:"Winter",2:"Winter",
         3:"Spring",4:"Spring",5:"Spring",
         6:"Summer",7:"Summer",8:"Summer",
         9:"Autumn",10:"Autumn",11:"Autumn"}
    )
    return df


# -- Task 2.1: Total Wind/PV forecasted production ----------------------------------------

def task_2_1(df: pd.DataFrame):
    """
    Total forecasted MWh for 2021 on DA and ID.
    """
    factor = 0.25  # 15 min = 0.25 h

    results = {
        "Wind DA [TWh]": df["wind_da_mw"].sum() * factor / 1e6,
        "Wind ID [TWh]": df["wind_id_mw"].sum() * factor / 1e6,
        "PV DA   [TWh]": df["pv_da_mw"].sum()   * factor / 1e6,
        "PV ID   [TWh]": df["pv_id_mw"].sum()   * factor / 1e6,
    }

    print("\n-- Task 2.1: --Total Forecasted Production 2021----------------")
    for k, v in results.items():
        print(f"  {k}: {v:.1f} TWh  ({v*1e6:,.0f} MWh)")

    # Bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ["Wind DA", "Wind ID", "PV DA", "PV ID"]
    values = [v * 1e6 for v in results.values()]
    colors = [BLUE, "#4fa3e0", ORANGE, "#ffb347"]
    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2e6,
                f"{val/1e6:.1f} TWh", ha="center", va="bottom", fontsize=10)
    ax.set_title("Total Forecasted Wind & PV Production, DE 2021")
    ax.set_ylabel("Total Generation [MWh]")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x/1e6:.0f} TWh"))
    ax.set_ylim(0, max(values)*1.15)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_1_total_production.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_1_total_production.png")


# -- Task 2.2: Average 24h profile ----------------------------------------

def task_2_2(df: pd.DataFrame):
    """
    Average wind/PV production over a 24h period (by hour of day).
    QH data grouped to H mean.
    """
    hourly = df.groupby(df.index.hour)[
        ["wind_da_mw","wind_id_mw","pv_da_mw","pv_id_mw"]
    ].mean()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    # Wind
    ax1.plot(hourly.index, hourly["wind_da_mw"], color=BLUE,   lw=2, label="Wind DA", marker="o", ms=4)
    ax1.plot(hourly.index, hourly["wind_id_mw"], color="#4fa3e0", lw=2, ls="--", label="Wind ID", marker="s", ms=4)
    ax1.set_title("Wind – Average Hourly Profile 2021")
    ax1.set_xlabel("Hour of Day")
    ax1.set_ylabel("Average Power [MW]")
    ax1.set_xticks(range(0, 24, 2))
    ax1.legend()

    # Solar
    ax2.plot(hourly.index, hourly["pv_da_mw"], color=ORANGE, lw=2, label="PV DA", marker="o", ms=4)
    ax2.plot(hourly.index, hourly["pv_id_mw"], color="#ffb347", lw=2, ls="--", label="PV ID", marker="s", ms=4)
    ax2.set_title("Solar – Average Hourly Profile 2021")
    ax2.set_xlabel("Hour of Day")
    ax2.set_ylabel("Average Power [MW]")
    ax2.set_xticks(range(0, 24, 2))
    ax2.legend()

    fig.suptitle("Average Wind & Solar Production over 24 hrs, DE 2021",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_2_24h_profile.png"), dpi=150)
    plt.close(fig)
    print("\n--- Task 2.2 --- 24h Production Profiles saved")
    print("  Saved task2_2_24h_profile.png")


# -- Task 2.3: Average value of Wind/PV power ----------------------------------------

def task_2_3(df: pd.DataFrame):
    """
    Value of Wind/PV = weighted average DA price, weighted by DA forecast.
    Compare to simple average DA price.

    MW-weighted average = sum(forecast_mw * price) / sum(forecast_mw)
    """
    avg_da = df["da_price"].mean()

    wind_value = (df["wind_da_mw"] * df["da_price"]).sum() / df["wind_da_mw"].sum()
    pv_value   = (df["pv_da_mw"]   * df["da_price"]).sum() / df["pv_da_mw"].sum()

    print("\n ---- Task 2.3: -- Average Value of Wind/PV Power 2021 -------")
    print(f"  Average DA price        : €{avg_da:.2f}/MWh")
    print(f"  Average value of Wind   : €{wind_value:.2f}/MWh  ({wind_value-avg_da:+.2f} vs avg)")
    print(f"  Average value of PV     : €{pv_value:.2f}/MWh  ({pv_value-avg_da:+.2f} vs avg)")

    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Avg DA Price", "Wind Value", "PV Value"]
    vals   = [avg_da, wind_value, pv_value]
    colors = [GREEN, BLUE, ORANGE]
    bars = ax.bar(labels, vals, color=colors, width=0.45, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                f"€{v:.2f}", ha="center", fontsize=11)
    ax.axhline(avg_da, color=GREEN, lw=1.5, ls="--", alpha=0.7, label=f"Avg DA = €{avg_da:.1f}")
    ax.set_title("Capture Value vs Average DA Price, 2021")
    ax.set_ylabel("EUR/MWh")
    ax.set_ylim(0, max(vals)*1.15)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_3_capture_value.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_3_capture_value.png")


# -- Task 2.4: Highest/Lowest renewable day ----------------------------------------

def task_2_4(df: pd.DataFrame):
    """Find day with highest and lowest combined wind+PV production (DA forecast)."""
    # Daily total in MWh (sum of 15-min MW * 0.25)
    daily = df.groupby("date").agg(
        wind_da_mwh=("wind_da_mw", lambda x: x.sum() * 0.25),
        pv_da_mwh  =("pv_da_mw",   lambda x: x.sum() * 0.25),
        avg_da_price=("da_price",   "mean"),
    )
    daily["total_re_mwh"] = daily["wind_da_mwh"] + daily["pv_da_mwh"]

    max_day = daily["total_re_mwh"].idxmax()
    min_day = daily["total_re_mwh"].idxmin()

    print("\n----- Task 2.4:--Highest / Lowest Renewable Day 2021------------")
    print(f"  Highest RE day : {max_day}  |  RE = {daily.loc[max_day,'total_re_mwh']:,.0f} MWh"
          f"  |  Avg DA price = €{daily.loc[max_day,'avg_da_price']:.1f}/MWh")
    print(f"  Lowest  RE day : {min_day}  |  RE = {daily.loc[min_day,'total_re_mwh']:,.0f} MWh"
          f"  |  Avg DA price = €{daily.loc[min_day,'avg_da_price']:.1f}/MWh")

    # Scatter: daily RE vs avg DA price
    fig, ax = plt.subplots(figsize=(9, 5))
    sc = ax.scatter(daily["total_re_mwh"]/1e3, daily["avg_da_price"],
                    c=daily["avg_da_price"], cmap="RdYlGn_r", alpha=0.6, s=20, edgecolors="none")
    # Highlight extremes
    for day, color, label in [(max_day, RED, "Max RE"), (min_day, GREEN, "Min RE")]:
        ax.scatter(daily.loc[day,"total_re_mwh"]/1e3, daily.loc[day,"avg_da_price"],
                   color=color, s=120, zorder=5, label=f"{label} ({day})")
    # Regression line
    m, b, r, p, _ = stats.linregress(daily["total_re_mwh"], daily["avg_da_price"])
    xs = np.linspace(daily["total_re_mwh"].min(), daily["total_re_mwh"].max(), 100)
    ax.plot(xs/1e3, m*xs+b, "k--", lw=1.5, alpha=0.6, label=f"Trend (r={r:.2f})")
    plt.colorbar(sc, ax=ax, label="Avg DA Price [EUR/MWh]")
    ax.set_title("Daily Renewable Production vs DA Price, DE 2021")
    ax.set_xlabel("Total Wind+PV [GWh/day]")
    ax.set_ylabel("Average DA Price [EUR/MWh]")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_4_re_vs_price.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_4_re_vs_price.png")


# -- Task 2.5: Weekday vs Weekend DA prices -----------------------------------------

def task_2_5(df: pd.DataFrame):
    """Average hourly DA price on weekdays vs weekends."""
    hourly = df.groupby([df.index.hour, "is_weekend"])["da_price"].mean().unstack()
    hourly.columns = ["Weekday", "Weekend"]

    avg_wd = df.loc[~df["is_weekend"], "da_price"].mean()
    avg_we = df.loc[df["is_weekend"],  "da_price"].mean()

    print("\n---- Task 2.5:---Weekday vs Weekend DA Price 2021 ----------")
    print(f"  Avg weekday DA price : €{avg_wd:.2f}/MWh")
    print(f"  Avg weekend DA price : €{avg_we:.2f}/MWh")
    print(f"  Difference           : €{avg_wd-avg_we:+.2f}/MWh")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hourly.index, hourly["Weekday"], color=BLUE,   lw=2.5, label=f"Weekday (avg €{avg_wd:.1f})", marker="o", ms=4)
    ax.plot(hourly.index, hourly["Weekend"], color=ORANGE, lw=2.5, label=f"Weekend (avg €{avg_we:.1f})", marker="s", ms=4)
    ax.fill_between(hourly.index, hourly["Weekday"], hourly["Weekend"], alpha=0.1, color=BLUE)
    ax.set_title("Avg Hourly DA Price: Weekday vs Weekend, 2021")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Average DA Price [EUR/MWh]")
    ax.set_xticks(range(0, 24, 1))
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_5_weekday_weekend.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_5_weekday_weekend.png")


# -- Task 2.6: Battery revenue -----------------------------------------------------

def task_2_6(df: pd.DataFrame):
    """
    1 MWh battery, 1 charge+discharge cycle per day.
    Optimal strategy: buy at hourly DA minimum, sell at hourly DA maximum.
    Revenue = sell_price - buy_price  (in EUR, since capacity = 1 MWh).
    Charge price must occur before discharge price.
    """
    # Work on hourly resolution
    hourly_da = df["da_price"].resample("h").first()  # DA price is same for all 4 QH in an hour

    total_revenue = 0.0
    daily_revenues = []

    for date, group in hourly_da.groupby(hourly_da.index.date):
        prices = group.values
        hours  = group.index.hour

        # Find best buy (min) hour, then best sell (max) hour AFTER buy
        best_rev = 0.0
        for i in range(len(prices)):
            for j in range(i+1, len(prices)):
                rev = prices[j] - prices[i]
                if rev > best_rev:
                    best_rev = rev
        total_revenue += best_rev
        daily_revenues.append({"date": pd.Timestamp(date), "revenue": best_rev})

    rev_df = pd.DataFrame(daily_revenues).set_index("date")

    print("\n------Task 2.6:----Battery Revenue 2021 ------------------------------")
    print(f"  Total annual revenue (1 MWh battery): €{total_revenue:,.2f}")
    print(f"  Average daily revenue                : €{total_revenue/365:.2f}")
    print(f"  Days with positive spread            : {(rev_df['revenue']>0).sum()}")

    # Cumulative revenue plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    cum_rev = rev_df["revenue"].cumsum()
    ax1.fill_between(cum_rev.index, cum_rev.values, alpha=0.3, color=GREEN)
    ax1.plot(cum_rev.index, cum_rev.values, color=GREEN, lw=2)
    ax1.set_title(f"Cumulative Battery Revenue 2021  |  Total: €{total_revenue:,.0f}")
    ax1.set_ylabel("Cumulative Revenue [EUR]")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    ax2.bar(rev_df.index, rev_df["revenue"], color=GREEN, alpha=0.7, width=1)
    ax2.axhline(total_revenue/365, color=RED, lw=1.5, ls="--", label=f"Daily avg €{total_revenue/365:.1f}")
    ax2.set_title("Daily Battery Revenue")
    ax2.set_ylabel("Revenue [EUR/day]")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax2.legend()

    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_6_battery_revenue.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_6_battery_revenue.png")

    return rev_df


# -- Transaction cost model -------------------------------------------

def compute_tc() -> dict:
    """
    Rough order-of-magnitude round-trip transaction costs (TC). For more details and 
    limitations see Readme.

    Total TC = fee (0.10) + execution/bid-ask (0.63) + permanent market impact (0.10)
    = 0.83 eur/MWh

    """
    fee    = 0.10 
    bidask = 0.63 
    # Permanent market impact
    impact = 0.10 

    total = fee + bidask + impact
    results = {}
    for product_name in ["hourly", "15min"]:
        results[product_name] = {
            "fee":    fee,
            "bidask": bidask,
            "impact": impact,
            "total":  total,
        }
    return results


# -- Task 2.7: Trading Strategies --------------------------------------------

def task_2_7(df: pd.DataFrame):
    """
    3 trading strategies.

    -- Strategy A: Hourly RE Forecast Revision (DA->ID Hourly) 
    SIGNAL:
      ΔRE = (wind_id + pv_id) − (wind_da + pv_da)   [MW]
      Both inputs are available before the intraday market closes (should be lookahead-free).
      Signal is just the sign of ΔRE.

    HYPOTHESIS:
      ΔRE > 0 -> more supply than DA priced in -> ID < DA -> SHORT spread
      ΔRE < 0 -> less supply than DA priced in -> ID > DA -> LONG  spread

    EXECUTION:
      Sell/buy 100 MW on DA at the published hourly auction price. Close against
      the id_price_h, which is described as "realized Intraday price on the hourly markets". 
      It would be good to know the exact aggregation, as this matters for TC. But as everything 
      is already simplified and approximate, just use TC as rough order-of-magnitude idea.

    -- Strategy B: QH RE Forecast Revision (DA->ID 15-min) 
    Same signal, executed on 15-min continuous product.
    Position still 100 MW, but split into 4x 25 MWh QH orders.
    In reality should have lower bid-ask than hourly; introduces basis risk vs the hourly DA price.
 
    -- Strategy C: see below.
    """

    POSITION_MW  = 100
    MWH_H        = POSITION_MW * 1.0
    MWH_QH       = POSITION_MW * 0.25

    # ── TC model -----------------------------------
    tc = compute_tc()
    TC_HOURLY = tc["hourly"]["total"]
    TC_15MIN  = tc["15min"]["total"]

    print("\n----Task 2.7:-----Transaction Cost Model --------------------")
    t = tc["hourly"]  # same for all
    print(f"  TC = fee {t['fee']:.2f} + bid-ask {t['bidask']:.2f} + "
          f"impact {t['impact']:.2f} = {t['total']:.2f} EUR/MWh  ")

    # ── Strategy A: hourly ---------------------------------
    hourly = df.resample("h").agg(
        wind_da  =("wind_da_mw", "mean"),
        wind_id  =("wind_id_mw", "mean"),
        pv_da    =("pv_da_mw",   "mean"),
        pv_id    =("pv_id_mw",   "mean"),
        da_price =("da_price",   "first"),
        id_price =("id_price_h", "first"),
        month    =("month",      "first"),
        #hour     =("hour",       "first"),
    ).dropna()

    hourly["delta_re"]     = ((hourly["wind_id"] + hourly["pv_id"])
                             - (hourly["wind_da"]  + hourly["pv_da"]))
    hourly["da_id_spread"] = hourly["da_price"] - hourly["id_price"]
    hourly["position"]     = -np.sign(hourly["delta_re"])
    hourly["pnl_gross"]    = hourly["position"] * (hourly["id_price"] - hourly["da_price"]) * MWH_H
    hourly["pnl_net"]      = hourly["pnl_gross"] - TC_HOURLY * MWH_H

    daily_A = hourly[["pnl_gross", "pnl_net"]].resample("D").sum()
    gA, nA  = hourly["pnl_gross"].sum(), hourly["pnl_net"].sum()
    shA_n   = daily_A["pnl_net"].mean()   / daily_A["pnl_net"].std()   * np.sqrt(252)
    wrA     = (hourly["pnl_gross"] > 0).mean() * 100

    # ── Strategy B: 15-min -------------------------------------------------
    
    qh = df.copy()
    qh["delta_re"] = ((qh["wind_id_mw"] + qh["pv_id_mw"])
                     - (qh["wind_da_mw"] + qh["pv_da_mw"]))
    qh["position"] = -np.sign(qh["delta_re"])
    qh["pnl_gross"] = qh["position"] * (qh["id_price_15"] - qh["da_price"]) * MWH_QH
    qh["pnl_net"]   = qh["pnl_gross"] - TC_15MIN * MWH_QH

    daily_B = qh[["pnl_gross", "pnl_net"]].resample("D").sum()
    gB, nB  = qh["pnl_gross"].sum(), qh["pnl_net"].sum()
    wrB     = (qh["pnl_gross"] > 0).mean() * 100

    
    # ── Strategy C: 15-min, proportional position sizing ---------------------------    
    """
    MAX_POSITION_MW = 100
    p95_delta_re = qh["delta_re"].abs().quantile(0.95)
    qh["scalar_C"] = (qh["delta_re"].abs() / p95_delta_re).clip(0, 1)
    qh["position_C"] = -np.sign(qh["delta_re"]) * qh["scalar_C"]
    qh["mwh_C"] = qh["scalar_C"] * MAX_POSITION_MW * 0.25   # variable MWh per QH

    qh["pnl_C_gross"] = qh["position_C"] * (qh["id_price_15"] - qh["da_price"]) * MAX_POSITION_MW * 0.25
    qh["pnl_C_net"]   = qh["pnl_C_gross"] - TC_15MIN * qh["scalar_C"] * MWH_QH

    daily_C = qh[["pnl_C_gross", "pnl_C_net"]].resample("D").sum()
    gC, nC  = qh["pnl_C_gross"].sum(), qh["pnl_C_net"].sum()
    shC_n   = daily_C["pnl_C_net"].mean() / daily_C["pnl_C_net"].std() * np.sqrt(252)
    wrC     = (qh["pnl_C_gross"] > 0).mean() * 100
    avg_pos_C = qh["scalar_C"].mean() * 100  # avg effective MW"""
    

    # ── Strategy C: 15-min, proportional position sizing ──────────────────────
    # Position proportional to how unusual |ΔRE| is, conditioned on
    # hour-of-day — a z-score within each hour's recent history.
    # Motivation: seasonal structure, a X MW revision in summer is surprising (strong signal);
    # the same revision in winter is not (weak signal).
    #
    # z = (|ΔRE| - rolling_mean_same_hour) / rolling_std_same_hour
    # scalar = clip(z, 0, 1)
    #   0 -> at or below conditional mean -> no position (unsurprising revision)
    #   1 -> >=1 conditional std above mean -> full 100 MW position
    #
    # Rolling window: 30 days of same-hour observations (30 obs per hour).
    # shift(1) on the rolling stats for no look-ahead.
    # Limitation: 30-day window is a free parameter
    # (one month of same-hour history) but should be validated OOS.
    
    MAX_POSITION_MW = 100
    qh["hour"]    = qh.index.hour
    qh["abs_dre"] = qh["delta_re"].abs()
    
    qh["roll_mean"] = (qh.groupby("hour")["abs_dre"]
                         .transform(lambda x: x.shift(1).rolling(30, min_periods=5).mean()))
    qh["roll_std"]  = (qh.groupby("hour")["abs_dre"]
                         .transform(lambda x: x.shift(1).rolling(30, min_periods=5).std()))
    
    qh["scalar_C"]   = ((qh["abs_dre"] - qh["roll_mean"])
                         / qh["roll_std"].replace(0, np.nan)).clip(0, 1).fillna(0)
    qh["position_C"] = -np.sign(qh["delta_re"]) * qh["scalar_C"]
    
    qh["pnl_C_gross"] = qh["position_C"] * (qh["id_price_15"] - qh["da_price"]) * MAX_POSITION_MW * 0.25
    qh["pnl_C_net"]   = qh["pnl_C_gross"] - TC_15MIN * qh["scalar_C"] * MWH_QH
    
    daily_C   = qh[["pnl_C_gross", "pnl_C_net"]].resample("D").sum()
    gC, nC    = qh["pnl_C_gross"].sum(), qh["pnl_C_net"].sum()
    wrC       = (qh["pnl_C_gross"] > 0).mean() * 100
    avg_pos_C = qh["scalar_C"].mean() * 100
    

    # ── Metrics defs -------------------------
    def maxdd(s):
        cs = s.cumsum()
        return (cs - cs.cummax()).min()

    def sharpe(daily_s):
        return daily_s.mean() / daily_s.std() * np.sqrt(365)

    def sortino(daily_s):
    #semi-dev: sqrt(mean of squared neg dev), all days
        semi_dev = np.sqrt((np.minimum(daily_s, 0) ** 2).mean())
        if semi_dev == 0: return np.nan
        return daily_s.mean() / semi_dev * np.sqrt(365)

    def calmar(daily_s):
    # Annual PnL / |max peak-to-trough drawdown|
        dd = maxdd(daily_s)
        return daily_s.sum() / abs(dd) if dd != 0 else np.nan

    
    metrics = {}
    active_masks = {
        "A": hourly["pnl_gross"] != 0,
        "B": qh["pnl_gross"] != 0,
        "C": qh["scalar_C"] > 0,   # use scalar directly — pnl_C_gross can be near-zero for tiny scalars
    }
    for name, daily_s, gross, net, pnl_gross_series in [
        ("A", daily_A["pnl_net"],   gA, nA, hourly["pnl_gross"]),
        ("B", daily_B["pnl_net"],   gB, nB, qh["pnl_gross"]),
        ("C", daily_C["pnl_C_net"], gC, nC, qh["pnl_C_gross"]),
    ]:
        dd   = maxdd(daily_s)
        act  = active_masks[name]
        wr_active = (pnl_gross_series[act] > 0).mean() * 100 if act.any() else 0
        wr_daily  = (daily_s > 0).mean() * 100
        metrics[name] = dict(
            gross=gross, net=net,
            tc_pct=(gross-net)/gross*100 if gross else 0,
            sharpe=sharpe(daily_s),
            sortino=sortino(daily_s),
            calmar=calmar(daily_s),
            wr=wr_active,
            wr_daily=wr_daily,
            dd=dd,
        )

    # ── Print results ──────────────────────────────────────────────────────────
    print("\n-----Strategy Results ---------")
    hdr = (f"  {'Strategy':<38} {'Net PnL':>12} {'TC%':>5} "
           f"{'Sharpe':>7} {'WR(active)':>11} {'WR(daily)':>10} {'MaxDD(p-t)':>12}")
    print(hdr)
    print("  " + "─" * 102)
    labels = {
        "A": "A: Hourly  (binary)",
        "B": "B: 15-min  (binary)",
        "C": "C: 15-min  (z-score sizing)",
    }
    for k, m in metrics.items():
        print(f"  {labels[k]:<38} €{m['net']:>10,.0f} {m['tc_pct']:>4.1f}% "
              f"{m['sharpe']:>7.2f} {m['wr']:>10.1f}% {m['wr_daily']:>9.1f}% {m['dd']:>12,.0f}")

    
    # ── Figure 1: Cumulative PnL --------------------------
    fig, axes = plt.subplots(3, 1, figsize=(14, 15))

    ax = axes[0]
    for series, color, key in [
        (daily_A["pnl_net"].cumsum(),   BLUE,   "A"),
        (daily_B["pnl_net"].cumsum(),   GREEN,  "B"),
        (daily_C["pnl_C_net"].cumsum(), PURPLE, "C"),
    ]:
        m = metrics[key]
        lbl = (f"{key}  net €{m['net']/1e6:.2f}M  "
               f"Sh={m['sharpe']:.1f}  So={m['sortino']:.1f}  Cal={m['calmar']:.1f} DD={m['dd']:.1f} WinRate={m['wr']:.1f}%")
        ax.plot(series.index, series.values, lw=2, color=color, label=lbl)
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.set_title("Task 2.7 – Cumulative Net PnL (max 100 MW, 2021)")
    ax.set_ylabel("Cumulative PnL [EUR]")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x/1e6:.1f}M"))
    ax.legend(fontsize=9)

    # ── Figure 2: Signal validation -------------
    ax = axes[1]
    sc = ax.scatter(
        hourly["delta_re"] / 1e3, hourly["da_id_spread"],
        c=hourly["pnl_gross"], cmap="RdYlGn",
        alpha=0.3, s=8, vmin=-5e3, vmax=5e3
    )
    ax.axhline(0, color="black", lw=0.8, ls=":")
    ax.axvline(0, color="grey",  lw=0.8, ls=":")
    m, b, r, *_ = stats.linregress(hourly["delta_re"], hourly["da_id_spread"])
    xs = np.linspace(hourly["delta_re"].min(), hourly["delta_re"].max(), 200)
    ax.plot(xs / 1e3, m * xs + b, "k-", lw=2, label=f"OLS trend  r={r:.2f}")
    plt.colorbar(sc, ax=ax, label="Hourly gross PnL [EUR]")
    ax.set_title("Signal Validation: ΔRE Forecast vs Realized DA−ID Spread")
    ax.set_xlabel("ΔRE (ID − DA forecast) [GW]")
    ax.set_ylabel("Realized DA − ID Price [EUR/MWh]")
    ax.legend(fontsize=10)

    # ── Figure 3: Monthly net PnL — A, B, C --------
    ax = axes[2]
    months_lbl = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    x, w = np.arange(12), 0.25
    for offset, col, daily, label, color in [
        (-w,  "pnl_net",   daily_A, "A  hourly",              BLUE),
        ( 0,  "pnl_net",   daily_B, "B  15-min binary",       GREEN),
        ( w,  "pnl_C_net", daily_C, "C  proportional sizing", PURPLE),
    ]:
        monthly = daily[col].resample("ME").sum() / 1e3
        vals = [monthly[monthly.index.month == m].sum() for m in range(1, 13)]
        ax.bar(x + offset, vals, width=w, label=label,
               color=color, alpha=0.85, edgecolor="white")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(months_lbl)
    ax.set_title("Monthly Net PnL: All Strategies (after TC)")
    ax.set_ylabel("Net PnL [k€]")
    ax.legend(fontsize=9)

    fig.tight_layout(pad=2.5)
    fig.savefig(os.path.join(PLOTS_DIR, "task2_7_strategy.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_7_strategy.png")

    # ── Figure 4: Intra-hour momentum ------
    # For each QH slot (0--3 within each delivery hour), compute deviation
    # from that hour's mean ID price.
    qh["qh_slot"] = qh.index.minute // 15
    qh["id_hour_mean"] = qh.groupby(qh.index.floor("h"))["id_price_15"].transform("mean")
    qh["id_dev"] = qh["id_price_15"] - qh["id_hour_mean"]

    # Overall mean deviation by slot
    slot_mean = qh.groupby("qh_slot")["id_dev"].mean()
    slot_std  = qh.groupby("qh_slot")["id_dev"].std() / np.sqrt(len(qh) / 4)  # SE

    # Deviation by hour-of-day × slot (heat map)
    pivot = qh.pivot_table(values="id_dev", index=qh.index.hour,
                           columns="qh_slot", aggfunc="mean")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Panel 1: overall average deviation +- 1 SE
    slots = [0, 1, 2, 3]
    labels_s = ["XX:00", "XX:15", "XX:30", "XX:45"]
    colors_s = [RED if v > 0 else BLUE for v in slot_mean.values]
    ax1.bar(slots, slot_mean.values, color=colors_s, alpha=0.8, edgecolor="white",
            yerr=slot_std.values, capsize=4, width=0.6)
    ax1.axhline(0, color="black", lw=1)
    ax1.set_xticks(slots); ax1.set_xticklabels(labels_s)
    ax1.set_title("Mean 15-min Price Deviation from Hourly Mean\n(all hours & months, 2021)")
    ax1.set_ylabel("EUR/MWh")
    for i, v in enumerate(slot_mean.values):
        ax1.text(i, v + (0.15 if v >= 0 else -0.25), f"{v:+.2f}",
                 ha="center", fontsize=9, fontweight="bold")

    # Panel 2: heatmap of deviation by hour-of-day
    import matplotlib.colors as mcolors
    norm = mcolors.TwoSlopeNorm(vmin=pivot.values.min(), vcenter=0,
                                vmax=pivot.values.max())
    im = ax2.imshow(pivot.values, aspect="auto", cmap="RdBu_r", norm=norm)
    ax2.set_xticks(slots); ax2.set_xticklabels(labels_s)
    ax2.set_yticks(range(24))
    ax2.set_yticklabels([f"{h:02d}:00" for h in range(24)], fontsize=7)
    ax2.set_title("15-min Price Deviation× QH Slot\n(red=above mean, blue=below)")
    ax2.set_xlabel("QH slot within hour")
    ax2.set_ylabel("Delivery hour")
    plt.colorbar(im, ax=ax2, label="EUR/MWh deviation")

    fig.suptitle("Intra-Hour Price Pattern",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_7_intrahour.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_7_intrahour.png")

    return hourly, qh, daily_C


# -- Task 2.7: Imbalance Analysis -----------------------------------------------

def task_2_7_imbalance(df: pd.DataFrame, hourly: pd.DataFrame, qh: pd.DataFrame):
    """
    reBAP (German balancing settlement price) can be used as a diagnostic: does the 
    ΔRE-based position agree with system stress direction?

    Alignment > 50%: ID price movement directional with grid stress, < 50% -- decoupled.
    """
    imb      = qh["imbalance_price"]
    pos_B    = qh["position"]                       # binary 
    #pos_C    = qh["position_C"]                     # proportional

    # Assuming: system long (imb<0) -> short spread correct -> pos should be -1
    # system short (imb>0) -> long spread correct -> pos should be +1
    # i.e. aligned when sign(pos) == sign(imb)
    valid = imb != 0
    align_B = (np.sign(pos_B[valid]) == np.sign(imb[valid])).mean() * 100
    #align_C = (np.sign(pos_C[valid]) == np.sign(imb[valid])).mean() * 100

    # Alignment conditional on winning / losing QH (Strategy B)
    win  = qh["pnl_gross"] > 0
    align_win  = (np.sign(pos_B[valid & win])  == np.sign(imb[valid & win])).mean()  * 100
    align_loss = (np.sign(pos_B[valid & ~win]) == np.sign(imb[valid & ~win])).mean() * 100

    # Alignment by |imbalance price| quintile
    quintiles   = pd.qcut(imb[valid].abs(), 5,
                          labels=["Q1(calm)","Q2","Q3","Q4","Q5(stressed)"])
    align_by_q  = (np.sign(pos_B[valid]) == np.sign(imb[valid])).groupby(quintiles).mean() * 100

    # Correlation: impalance price vs DA-ID spread and delta_RE
    da_id_qh = qh["da_price"] - qh["id_price_15"]
    v = imb.notna() & da_id_qh.notna()
    corr_spread  = np.corrcoef(da_id_qh[v], imb[v])[0, 1]
    v2 = imb.notna() & qh["delta_re"].notna()
    corr_delta   = np.corrcoef(qh["delta_re"][v2], imb[v2])[0, 1]


    # -- Figure: 3-panel validation plot ---------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Panel 1: imbalance price distribution
    ax = axes[0]
    ax.hist(imb, bins=80, color=BLUE, alpha=0.7, edgecolor="white")
    ax.axvline(0, color="black", lw=1, ls="--")
    ax.set_title("reBAP distribution")
    ax.set_xlabel("reBAP [EUR/MWh]"); ax.set_ylabel("Count")
    #transform=ax.transAxes, ha="right", va="top", fontsize=9, color=RED)

    # Panel 2: alignment by imbalance price quintile
    ax = axes[1]
    vals  = list(align_by_q.values)
    clrs  = [GREEN if v >= 50 else RED for v in vals]
    lbls  = [str(q) for q in align_by_q.index]
    ax.bar(range(5), vals, color=clrs, alpha=0.85, edgecolor="white")
    ax.axhline(50,       color="black", lw=1,   ls="--", label="50%")
    ax.axhline(align_B,  color=GREEN,   lw=1.5, ls="--",
               label=f"B overall {align_B:.1f}%")
    ax.set_xticks(range(5)); ax.set_xticklabels(lbls, fontsize=8)
    ax.set_title("Position Alignment with System Stress by Quintile")
    ax.set_ylabel("% QH slots aligned"); ax.set_ylim(30, 70)
    ax.legend(fontsize=9)

    # Panel 3: monthly avg imbalance price vs strategy B net PnL
    ax   = axes[2]
    ax2r = ax.twinx()
    months_lbl = ["J","F","M","A","M","J","J","A","S","O","N","D"]
    m_imb = imb.resample("ME").mean()
    m_pnl = qh["pnl_net"].resample("ME").sum() / 1e3
    i_vals = [m_imb[m_imb.index.month == m].mean() for m in range(1, 13)]
    p_vals = [m_pnl[m_pnl.index.month == m].sum()  for m in range(1, 13)]
    ax.bar(range(12), i_vals, color=ORANGE, alpha=0.6, label="Avg reBAP")
    ax2r.plot(range(12), p_vals, color=GREEN, lw=2, marker="o",
              markersize=5, label="Strat B net PnL")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(12)); ax.set_xticklabels(months_lbl)
    ax.set_title("Monthly Avg reBAP vs Strat B Net PnL")
    ax.set_ylabel("Avg reBAP [EUR/MWh]", color=ORANGE)
    ax2r.set_ylabel("Net PnL [k€]", color=GREEN)
    lines1, lbl1 = ax.get_legend_handles_labels()
    lines2, lbl2 = ax2r.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lbl1 + lbl2, fontsize=9)

    fig.suptitle("Imbalance Validation: Position Alignment & Correlation",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "task2_7_imbalance_analysis.png"), dpi=150)
    plt.close(fig)
    print("  Saved task2_7_imbalance_analysis.png")


# -- Main ----------------------------------------

def main():
    print("Loading data...")
    df = load_data()
    print(f"  Loaded {len(df):,} rows  ({df.index.min().date()} -- {df.index.max().date()})")

    task_2_1(df)
    task_2_2(df)
    task_2_3(df)
    task_2_4(df)
    task_2_5(df)
    task_2_6(df)
    hourly, qh, daily_C = task_2_7(df)
    task_2_7_imbalance(df, hourly, qh)

    print("\n All tasks complete. Plots saved to task2/plots/")


if __name__ == "__main__":
    main()
