# Prometheus System Exporter

A Python system metrics exporter for Prometheus, with multi-threaded metric collection, per-metric alert debouncing, and Telegram webhook notifications.

## Features

- **CPU / memory / disk** metrics exposed in Prometheus format on `/metrics`
- **Multi-threaded design**: separate threads for collection, alerting, and health endpoint
- **Per-metric alert state machine**: each metric has its own alert flag, so an alert fires once on threshold crossing and resets only when the value returns to normal (no alert spam)
- **Telegram webhook integration** with configurable timeout
- **Dual logging**: console + file (`/opt/python/test_app.log`)
- **Configurable via environment variables and `config.json`**
- **`/health` endpoint** for liveness checks

## Metrics Exposed

| Metric | Type | Description |
|---|---|---|
| `cpu_server_usage` | Gauge | Current CPU usage (%) |
| `mem_server_usage` | Gauge | Current memory usage (%) |
| `disk_server_usage` | Gauge | Current disk usage (%) |
| `collect_total` | Counter | Total successful metric collections |
| `collect_errors_total` | Counter | Total failed collections |
| `alert_total` | Counter | Total alerts sent |

Success rate can be computed in PromQL as `collect_errors_total / collect_total`.

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOGGING_LEVEL` | `INFO` | Log level (DEBUG / INFO / WARNING / ERROR) |
| `PORT_NUMBER` | `8000` | Prometheus metrics port |
| `SLEEP_TIME` | `5` | Collection interval (seconds) |
| `CPU_THRESHOLD` | `80` | Local warning threshold for CPU (%) |
| `MEM_THRESHOLD` | `80` | Local warning threshold for memory (%) |
| `DISK_THRESHOLD` | `80` | Local warning threshold for disk (%) |

### `config.json`

Copy `config.json.example` to `config.json` and fill in your values:

```json
{
  "telegram": {
    "chat_id": "YOUR_CHAT_ID",
    "token": "YOUR_BOT_TOKEN",
    "url": "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage"
  },
  "threshold": {
    "cpu_threshold": 80,
    "mem_threshold": 80,
    "disk_threshold": 80
  }
}
```

## Usage

```bash
pip install psutil prometheus_client flask requests
python exporter.py
```

Endpoints:

- `http://localhost:8000/metrics` — Prometheus scrape endpoint
- `http://localhost:5000/health` — liveness check

## Notes & Limitations

This exporter uses `psutil`, which in a containerized environment reads host-level `/proc` for CPU and memory, and container-level filesystem for disk. The metrics are therefore **not cgroup-aware** and should not be used for production container monitoring. For real workloads, use `node-exporter` (node-level) and `cAdvisor` (container-level), both included in `kube-prometheus-stack`.

The `/health` endpoint currently only reflects whether Flask itself is responsive. A proper readiness check that monitors the collection thread's state is a known TODO.

This project is built as a learning exercise to demonstrate Prometheus client library usage, multi-threaded design, and alert state machine patterns — not as a replacement for industry-standard exporters.

## Requirements

- Python 3.8+
- Linux (psutil reads `/proc`)
