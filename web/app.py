"""
app.py  –  Network Monitoring System – Web Dashboard

Routes
------
  GET /              → main dashboard (event table + node status)
  GET /api/events    → JSON event feed (polled by JS every 3 s)
  GET /api/nodes     → JSON active-node status
  GET /api/perf      → JSON live performance metrics
  GET /api/perf/history  → JSON perf history for the RTT trend chart
"""

import json
import os
import sys
import time

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
import database
import state
from config import WEB_PORT

app = Flask(__name__)


# ── HTML dashboard ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── JSON API endpoints ────────────────────────────────────────────────────────

@app.route("/api/events")
def api_events():
    node_filter  = request.args.get("node",  "")
    event_filter = request.args.get("event", "")
    limit        = min(int(request.args.get("limit", 100)), 500)
    events = database.get_events(limit, node_filter, event_filter)
    return jsonify(events)


@app.route("/api/nodes")
def api_nodes():
    nodes = state.get_active_nodes()
    return jsonify(nodes)


@app.route("/api/perf")
def api_perf():
    with state.lock:
        p = dict(state.perf)
    # Add live throughput freshly computed
    p["events_per_sec"] = state.get_throughput_last_n_seconds(5)
    return jsonify(p)


@app.route("/api/perf/history")
def api_perf_history():
    rows = database.get_perf_history(limit=60)
    # Return in chronological order for the chart
    rows.reverse()
    return jsonify(rows)


@app.route("/api/rtt")
def api_rtt():
    since = float(request.args.get("since", time.time() - 300))
    stats = database.get_rtt_stats(since_ts=since)
    return jsonify(stats)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[WEB  ] Dashboard starting on http://0.0.0.0:{WEB_PORT}")
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, threaded=True)
