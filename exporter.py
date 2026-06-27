import psutil
import time
from prometheus_client import Gauge, start_http_server, Counter
import logging
import os
from flask import Flask
import threading
import requests
import json


# ============ Config ============

log_level = os.getenv("LOGGING_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/python/test_app.log")
    ]
)

port_number = int(os.getenv("PORT_NUMBER", "8000"))
sleep_time = int(os.getenv("SLEEP_TIME", "5"))
json_file = "config.json"

CPU_THRESHOLD = int(os.getenv("CPU_THRESHOLD", "80"))
MEM_THRESHOLD = int(os.getenv("MEM_THRESHOLD", "80"))
DISK_THRESHOLD = int(os.getenv("DISK_THRESHOLD", "80"))


# ============ Metrics & Globals ============

cpu_usage = Gauge("cpu_server_usage", "current cpu usage percent")
mem_usage = Gauge("mem_server_usage", "current mem usage percent")
disk_usage = Gauge("disk_server_usage", "current disk usage percent")
collect_total = Counter("collect_total", "how many times metrics collected")
collect_errors_total = Counter("collect_errors_total", "metric collection error count")
alert_total = Counter("alert_total", "Alert count")

cpu_alert = False
mem_alert = False
disk_alert = False


# ============ Health Check ============

app = Flask(__name__)

@app.route("/health")
def status():
    return {"status": "ok"}


# ============ Collection ============

def load_metric():
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        cpu_usage.set(cpu)
        mem_usage.set(mem)
        disk_usage.set(disk)
        collect_total.inc()
        logging.info("metric 提取成功")
        return cpu, mem, disk
    except Exception as e:
        collect_errors_total.inc()
        logging.error(e, exc_info=True)
        return None


def process():
    while True:
        try:
            result = load_metric()
            if result is None:
                time.sleep(sleep_time)
                continue

            cpu, mem, disk = result

            if cpu > CPU_THRESHOLD:
                logging.warning(f"警告：cpu 高负载 {cpu}%")
            if mem > MEM_THRESHOLD:
                logging.warning(f"警告：mem 高负载 {mem}%")
            if disk > DISK_THRESHOLD:
                logging.warning(f"警告：disk 高负载 {disk}%")

        except Exception as e:
            logging.error(e, exc_info=True)

        time.sleep(sleep_time)


# ============ Alerting ============

def load_json():
    with open(json_file, "r") as f:
        return json.load(f)


def send_telegram(url, chat_id, text):
    try:
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=5)
        alert_total.inc()
    except Exception as e:
        logging.error(f"telegram 发送失败: {e}", exc_info=True)


def send_message():
    global cpu_alert, mem_alert, disk_alert

    json_data = load_json()
    url = json_data["telegram"]["url"]
    chat_id = json_data["telegram"]["chat_id"]
    cpu_used = int(json_data["threshold"]["cpu_threshold"])
    mem_used = int(json_data["threshold"]["mem_threshold"])
    disk_used = int(json_data["threshold"]["disk_threshold"])

    while True:
        result = load_metric()
        if result is None:
            time.sleep(10)
            continue
        cpu_current, mem_current, disk_current = result

        text = (
            f"服务器异常超载\n"
            f"当前 cpu: {cpu_current}%\n"
            f"当前 mem: {mem_current}%\n"
            f"当前 disk: {disk_current}%"
        )

        if cpu_current > cpu_used:
            if not cpu_alert:
                send_telegram(url, chat_id, text)
                cpu_alert = True
        else:
            cpu_alert = False

        if mem_current > mem_used:
            if not mem_alert:
                send_telegram(url, chat_id, text)
                mem_alert = True
        else:
            mem_alert = False

        if disk_current > disk_used:
            if not disk_alert:
                send_telegram(url, chat_id, text)
                disk_alert = True
        else:
            disk_alert = False

        time.sleep(10)


# ============ Main ============

def main():
    start_http_server(port_number)
    threading.Thread(target=process, daemon=True).start()
    threading.Thread(target=send_message, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
