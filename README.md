# Network Event Monitoring System

A production-grade distributed network monitoring system built with raw UDP and TCP sockets in Python.  
Designed and evaluated against the Socket Programming – Jackfruit Mini Project rubric.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Agent Nodes (clients)                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Metric collectors: CPU · Memory · Latency · Disk │  │
│  │  Fernet encryption → UDP datagrams (port 9000)    │  │
│  │  ACK + retransmit reliability layer               │  │
│  │  RTT measurement → TLS control channel (port 9001)│  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │  UDP (encrypted)
           ┌───────────────┴──────────────────┐
           │        Server (udp_server.py)     │
           │  ┌───────────────────────────┐   │
           │  │  UDP Receiver thread      │   │  ← decrypt, validate seq,
           │  │  TLS Control thread (mTLS)│   │    ACK, detect loss
           │  │  Node Watchdog thread     │   │
           │  │  Perf Collector thread    │   │
           │  └───────────┬───────────────┘   │
           │              │ SQLite            │
           │         events.db                │
           └──────────────┬───────────────────┘
                          │  Flask REST API
           ┌──────────────┴───────────────────┐
           │       Web Dashboard (app.py)      │
           │  /api/events  /api/nodes          │
           │  /api/perf    /api/perf/history   │
           └──────────────────────────────────┘
```

### Communication channels

| Channel | Protocol | Port | Purpose |
|---------|----------|------|---------|
| Telemetry | UDP + Fernet | 9000 | High-frequency metrics; ACK-based reliability |
| Control | TCP + TLS 1.2+ (mTLS) | 9001 | Registration, RTT reports, key exchange |
| Dashboard | HTTP (Flask) | 5000 | Web UI, JSON API |

---

## Features

- **Raw socket programming** — explicit `socket.socket`, `bind`, `listen`, `recvfrom`, `sendto`
- **Dual-layer security** — Fernet (AES-128-CBC + HMAC-SHA256) on UDP payload + mutual TLS 1.2+ on the control channel
- **ACK + retransmit reliability** — every UDP datagram is acknowledged; unacknowledged packets are retransmitted up to `MAX_RETRIES` times
- **RTT measurement** — per-packet round-trip time computed from `sent_ms → ACK_ms`; P99 tracked and displayed
- **Sequence-number gap detection** — server detects reordered / dropped datagrams and maintains a per-node loss counter
- **Multi-client concurrency** — server dispatches each received packet to a new daemon thread; tested with 50+ simultaneous clients
- **Node watchdog** — background thread marks nodes `DOWN` and inserts a `NODE_DOWN` event if no heartbeat arrives within `NODE_TIMEOUT` seconds
- **Performance collector** — samples throughput and RTT every second; writes 10-second snapshots to SQLite
- **Stress-test suite** — `tests/stress_test.py` runs baseline, multi-client, and burst phases; prints before/after latency comparison

---

## Project Structure

```
nms/
├── certs/
│   └── gen_certs.sh          # Generates CA + server + client certificates
├── server/
│   ├── config.py             # All tunable parameters
│   ├── database.py           # SQLite layer (events, ack_log, perf_stats)
│   ├── state.py              # In-memory shared state (nodes, seq, throughput)
│   └── udp_server.py         # Main server entry point
├── client/
│   └── client.py             # Agent node (metrics + ACK + TLS registration)
├── web/
│   ├── app.py                # Flask dashboard + REST API
│   └── templates/
│       └── index.html        # Single-page dashboard (Chart.js)
├── tests/
│   └── stress_test.py        # Performance benchmark & stress test
└── requirements.txt
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate TLS certificates

```bash
chmod +x certs/gen_certs.sh
./certs/gen_certs.sh
```

This creates a self-signed CA and signs both server and client certificates (mutual TLS).

### 3. Start the server

```bash
cd server
python udp_server.py
```

Expected output:
```
============================================================
  Network Monitoring System – Server
  UDP telemetry : 0.0.0.0:9000
  TLS control   : 0.0.0.0:9001
============================================================
[UDP  ] Listening on 0.0.0.0:9000
[TLS  ] Control server on 0.0.0.0:9001  (mTLS)
[WTCH ] Node watchdog started
[PERF ] Performance collector started
```

### 4. Start the web dashboard

```bash
cd web
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

### 5. Start one or more clients

```bash
# Terminal 1
cd client && python client.py

# Terminal 2 (second agent, different node ID generated automatically)
cd client && python client.py
```

### 6. Run the stress test

```bash
# Make sure the server is running first
python tests/stress_test.py --clients 10 --packets 50
python tests/stress_test.py --clients 50 --packets 100 --burst
```

---

## Reliability Protocol (UDP)

```
Client                               Server
  │                                    │
  │── encrypt(node|seq|ts|event) ─────►│
  │                                    │  validate Fernet token
  │                                    │  check seq gap (loss detection)
  │                                    │  insert_event(DB)
  │◄── ACK|node|seq|server_ts_ms ──────│
  │                                    │
  │  RTT = ack_ms - sent_ms            │
  │  if timeout → retransmit (×3 max)  │
  │                                    │
  │── TLS: RTT_RECORD|... ────────────►│  (batched every 15 s)
  │◄── OK ─────────────────────────────│
```

Key properties:
- **Sequence numbers** detect gaps; the server logs each discontinuity.
- **ACK timeout** (`ACK_TIMEOUT = 2 s`) + **MAX_RETRIES = 3** gives up to 8 s total window before a packet is declared lost.
- **Cooldown** (`COOLDOWN_SECONDS = 15`) prevents alert flooding without suppressing sequence numbers.
- RTT records are shipped via TLS so the server can compute P99 accurately without UDP reliability concerns.

---

## Performance Evaluation

Run `tests/stress_test.py` with incrementally larger client counts to observe:

| Phase | Clients | Packets each | Expected observation |
|-------|---------|--------------|----------------------|
| Baseline | 1 | 20 | Sub-millisecond RTT on loopback |
| Stress | 10 | 50 | RTT rises slightly; zero loss expected |
| Stress | 50 | 100 | RTT ~2-5× baseline; monitor P99 |
| Burst | 50 | 100 | Packet loss may appear; retransmit mechanism kicks in |

The `stress_report.txt` file produced by the script provides the full before/after comparison:

```
  ┌─ Before vs After Summary ──────────────────────────────────────┐
  │  Avg RTT  baseline  : 0.412 ms
  │  Avg RTT  stress    : 1.847 ms   (Δ +1.435 ms)
  │  P99 RTT  baseline  : 0.791 ms
  │  P99 RTT  stress    : 6.203 ms   (Δ +5.412 ms)
  │  Loss     baseline  : 0.0 %
  │  Loss     stress    : 0.0 %
  └────────────────────────────────────────────────────────────────┘
```

---

## Security Design

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| UDP payload | Fernet (AES-128-CBC + HMAC-SHA256) | Confidentiality + integrity of all telemetry data |
| TLS control | TLS 1.2+ with mutual certificate auth | Channel confidentiality; prevents rogue servers/clients |
| Sequence numbers | Monotonic counter + gap detection | Replay detection; reorder / loss visibility |

---

## Configuration Reference (`server/config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `UDP_PORT` | 9000 | Telemetry port |
| `TCP_PORT` | 9001 | TLS control port |
| `FERNET_KEY` | (set) | Shared UDP encryption key |
| `ACK_TIMEOUT` | 2.0 s | Time to wait for ACK before retransmitting |
| `MAX_RETRIES` | 3 | Maximum retransmit attempts per packet |
| `HEARTBEAT_INTERVAL` | 5 s | Time between client heartbeats |
| `NODE_TIMEOUT` | 30 s | Seconds without heartbeat before NODE_DOWN |
| `CPU_THRESHOLD` | 75 % | Alert threshold for CPU usage |
| `MEMORY_THRESHOLD` | 80 % | Alert threshold for memory usage |
| `LATENCY_THRESHOLD` | 100 ms | Alert threshold for ICMP latency |
| `COOLDOWN_SECONDS` | 15 s | Minimum gap between identical alert events |

---

## Key Concepts Demonstrated

- Raw UDP and TCP socket creation, binding, and data transmission
- Symmetric encryption (Fernet) applied at the application layer over UDP
- Mutual TLS (mTLS) for the control channel using Python's `ssl` module
- Multi-threaded concurrent server with a shared-state concurrency model
- Sequence-number-based packet-loss detection
- ACK/retransmit reliability layer built on top of unreliable UDP
- RTT measurement and P99 latency tracking
- Performance benchmarking under concurrent load
- SQLite for persistent event storage with thread-safe access
