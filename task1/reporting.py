"""
Task 1: Minimal Reporting Tool
================================
Computes buy/sell volumes and per-strategy PnL from the EPEX trades SQLite database,
and exposes PnL as a REST API via Flask.
"""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "trades.sqlite")
TABLE = "epex_12_20_12_13"


def _get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Task 1.1 – Total buy / sell volume
# ---------------------------------------------------------------------------

def compute_total_buy_volume(db_path: str = DB_PATH) -> float:
    """Return the total quantity (MW) across all BUY trades."""
    with _get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT COALESCE(SUM(quantity), 0) FROM {TABLE} WHERE side = 'buy'"
        ).fetchone()
    return float(row[0])


def compute_total_sell_volume(db_path: str = DB_PATH) -> float:
    """Return the total quantity (MW) across all SELL trades."""
    with _get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT COALESCE(SUM(quantity), 0) FROM {TABLE} WHERE side = 'sell'"
        ).fetchone()
    return float(row[0])


# ---------------------------------------------------------------------------
# Task 1.2 – Strategy PnL
# ---------------------------------------------------------------------------

def compute_pnl(strategy_id: str, db_path: str = DB_PATH) -> float:
    """
    Compute the PnL (EUR) of a given strategy.

    Income per trade:
        SELL →  +quantity * price   (received money for electricity)
        BUY  →  -quantity * price   (paid money for electricity)

    Returns 0.0 if the strategy has no trades.
    """
    with _get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT side, quantity, price
            FROM {TABLE}
            WHERE strategy = ?
            """,
            (strategy_id,),
        ).fetchall()

    if not rows:
        return 0.0

    pnl = 0.0
    for row in rows:
        if row["side"] == "sell":
            pnl += row["quantity"] * row["price"]
        else:  # buy
            pnl -= row["quantity"] * row["price"]
    return pnl


def list_strategies(db_path: str = DB_PATH) -> list[str]:
    """Return a list of all unique strategy IDs in the database."""
    with _get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT DISTINCT strategy FROM {TABLE} ORDER BY strategy"
        ).fetchall()
    return [r["strategy"] for r in rows]


# ---------------------------------------------------------------------------
# Task 1.3 – Flask REST API
# ---------------------------------------------------------------------------

def create_app(db_path: str = DB_PATH):
    """
    Factory that creates and returns the Flask application.

    Routes
    ------
    GET /                       HTML dashboard (open in browser)
    GET /v1/pnl/<strategy_id>   JSON PnL for a strategy
    GET /v1/strategies          JSON list of all strategy IDs
    GET /v1/volumes             JSON total buy/sell volumes
    """
    from flask import Flask, jsonify, render_template_string

    app = Flask(__name__)

    DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FlexPower – Trade Reporting</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 2rem;
    }
    h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.25rem; }
    .subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 2rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .card {
      background: #1e2130; border: 1px solid #2d3348; border-radius: 10px;
      padding: 1.25rem 1.5rem;
    }
    .card .label { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 0.4rem; }
    .card .value { font-size: 1.9rem; font-weight: 700; }
    .card .unit  { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }
    .pos { color: #34d399; } .neg { color: #f87171; } .neu { color: #60a5fa; }
    table { width: 100%; border-collapse: collapse; background: #1e2130;
            border: 1px solid #2d3348; border-radius: 10px; overflow: hidden; }
    th { background: #161926; color: #94a3b8; font-size: 0.78rem;
         text-transform: uppercase; letter-spacing: .05em; padding: 0.75rem 1rem; text-align: left; }
    td { padding: 0.85rem 1rem; border-top: 1px solid #2d3348; font-size: 0.95rem; }
    tr:hover td { background: #252a3d; }
    .badge {
      display: inline-block; padding: 0.2rem 0.65rem; border-radius: 99px;
      font-size: 0.75rem; font-weight: 600;
    }
    .badge-buy  { background: #1e3a5f; color: #60a5fa; }
    .badge-sell { background: #3b1f2b; color: #f87171; }
    .section-title { font-size: 1rem; font-weight: 600; margin: 2rem 0 0.75rem; color: #cbd5e1; }
    .api-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .api-item {
      background: #1e2130; border: 1px solid #2d3348; border-radius: 8px;
      padding: 0.6rem 1rem; font-size: 0.85rem; display: flex; align-items: center; gap: 0.75rem;
    }
    .method { background: #14532d; color: #4ade80; padding: 0.15rem 0.5rem;
              border-radius: 4px; font-size: 0.72rem; font-weight: 700; font-family: monospace; }
    .endpoint { font-family: monospace; color: #93c5fd; }
    .desc { color: #64748b; font-size: 0.8rem; margin-left: auto; }
    a { color: #93c5fd; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .ts { color: #475569; font-size: 0.78rem; margin-top: 2rem; }
  </style>
</head>
<body>
  <h1>⚡ FlexPower Trade Reporting</h1>
  <p class="subtitle">EPEX delivery period: {{ delivery_period }}</p>

  <div class="grid">
    <div class="card">
      <div class="label">Total Buy Volume</div>
      <div class="value neu">{{ buy_vol }}</div>
      <div class="unit">MW</div>
    </div>
    <div class="card">
      <div class="label">Total Sell Volume</div>
      <div class="value neu">{{ sell_vol }}</div>
      <div class="unit">MW</div>
    </div>
    {% for s in strategies %}
    <div class="card">
      <div class="label">PnL – {{ s.id }}</div>
      <div class="value {% if s.pnl >= 0 %}pos{% else %}neg{% endif %}">
        {% if s.pnl >= 0 %}+{% endif %}€{{ "%.2f"|format(s.pnl) }}
      </div>
      <div class="unit">EUR</div>
    </div>
    {% endfor %}
  </div>

  <p class="section-title">All Trades</p>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Strategy</th><th>Side</th><th>Qty (MW)</th><th>Price (€/MWh)</th><th>Income (€)</th>
      </tr>
    </thead>
    <tbody>
      {% for t in trades %}
      <tr>
        <td style="color:#64748b">{{ t.id }}</td>
        <td>{{ t.strategy }}</td>
        <td><span class="badge badge-{{ t.side }}">{{ t.side.upper() }}</span></td>
        <td>{{ t.quantity }}</td>
        <td>{{ "%.2f"|format(t.price) }}</td>
        <td class="{% if t.income >= 0 %}pos{% else %}neg{% endif %}">
          {% if t.income >= 0 %}+{% endif %}€{{ "%.2f"|format(t.income) }}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <p class="section-title">API Endpoints</p>
  <div class="api-list">
    <div class="api-item">
      <span class="method">GET</span>
      <span class="endpoint">/v1/pnl/{strategy_id}</span>
      <span class="desc">PnL for a strategy — e.g.
        <a href="/v1/pnl/strategy_1">/v1/pnl/strategy_1</a>,
        <a href="/v1/pnl/strategy_2">/v1/pnl/strategy_2</a>
      </span>
    </div>
    <div class="api-item">
      <span class="method">GET</span>
      <span class="endpoint"><a href="/v1/strategies">/v1/strategies</a></span>
      <span class="desc">List all strategy IDs</span>
    </div>
    <div class="api-item">
      <span class="method">GET</span>
      <span class="endpoint"><a href="/v1/volumes">/v1/volumes</a></span>
      <span class="desc">Total buy / sell volumes</span>
    </div>
  </div>

  <p class="ts">Generated at {{ capture_time }}</p>
</body>
</html>
"""

    @app.route("/")
    def dashboard():
        """HTML dashboard — open http://127.0.0.1:5000 in a browser."""
        with _get_connection(db_path) as conn:
            rows = conn.execute(
                f"SELECT id, strategy, side, quantity, price FROM {TABLE} ORDER BY id"
            ).fetchall()

        trades = []
        for r in rows:
            income = r["quantity"] * r["price"] if r["side"] == "sell" \
                     else -r["quantity"] * r["price"]
            trades.append({
                "id":       r["id"],
                "strategy": r["strategy"],
                "side":     r["side"],
                "quantity": r["quantity"],
                "price":    r["price"],
                "income":   income,
            })

        strategies = [
            {"id": sid, "pnl": compute_pnl(sid, db_path=db_path)}
            for sid in list_strategies(db_path=db_path)
        ]

        return render_template_string(
            DASHBOARD_HTML,
            buy_vol         = int(compute_total_buy_volume(db_path=db_path)),
            sell_vol        = int(compute_total_sell_volume(db_path=db_path)),
            strategies      = strategies,
            trades          = trades,
            delivery_period = "2022-12-20  12:00 – 13:00",
            capture_time    = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @app.route("/v1/pnl/<strategy_id>", methods=["GET"])
    def get_pnl(strategy_id: str):
        value = compute_pnl(strategy_id, db_path=db_path)
        return jsonify({
            "strategy":     strategy_id,
            "value":        value,
            "unit":         "euro",
            "capture_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    @app.route("/v1/strategies", methods=["GET"])
    def get_strategies():
        return jsonify({"strategies": list_strategies(db_path=db_path)})

    @app.route("/v1/volumes", methods=["GET"])
    def get_volumes():
        return jsonify({
            "total_buy_volume_mw":  compute_total_buy_volume(db_path=db_path),
            "total_sell_volume_mw": compute_total_sell_volume(db_path=db_path),
            "unit":                 "MW",
            "delivery_period":      "2022-12-20 12:00–13:00",
        })

    return app


# ---------------------------------------------------------------------------
#  CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("Task 1.1 – Volumes")
    print(f"  Total BUY  volume : {compute_total_buy_volume():.0f} MW")
    print(f"  Total SELL volume : {compute_total_sell_volume():.0f} MW")

    print("\nTask 1.2 – PnL per strategy")
    for sid in list_strategies():
        print(f"  {sid}: €{compute_pnl(sid):,.2f}")

    print("\nTask 1.3 – Starting Flask API on http://127.0.0.1:5000")
    print("  Try: GET /v1/pnl/strategy_1")
    print("       GET /v1/strategies")
    print("       GET /v1/volumes")
    app = create_app()
    app.run(debug=True)
