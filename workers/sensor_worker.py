# workers/sensor_worker.py
import threading
import time
from services.sensor_processor import SensorProcessor
from services.db_services import DBService

processor = SensorProcessor()
db = DBService()

_queue = []
_lock  = threading.Lock()

def enqueue(data: dict):
    with _lock:
        _queue.append(data)

def start_worker(socketio, device_manager):
    def run():
        while True:
            batch = []
            with _lock:
                batch, _queue[:] = list(_queue), []

            for data in batch:
                device_id = data.get("device_id")
                if not device_id:
                    continue

                device_manager.touch(device_id)
                last_seen = device_manager.seconds_since(device_id)

                payload = {"device_id": device_id, "status": {"last_seen": last_seen}}

                # ── Accelerometer ─────────────────────────────────────────────
                if "accelerometer" in data:
                    result = processor.process(device_id, data["accelerometer"])
                    payload["accelerometer"] = result

                    prev = device_manager.get_state(device_id)
                    if result["state"] != prev:
                        device_manager.set_state(device_id, result["state"])
                        payload["event"] = f"State → {result['state']}"

                    db.log_sensor(device_id, "accelerometer", result)

                # ── Fall detection ────────────────────────────────────────────
                if data.get("fall_detected"):
                    payload["fall_detected"] = True
                    payload["event"] = "⚠ FALL DETECTED"
                    db.log_event(device_id, "fall_detected", {"timestamp": data.get("timestamp")})

                # ── GPS ───────────────────────────────────────────────────────
                if "gps" in data:
                    payload["gps"] = data["gps"]
                    db.log_sensor(device_id, "gps", data["gps"])

                # ── Battery ───────────────────────────────────────────────────
                if "battery" in data:
                    payload["battery"] = data["battery"]
                    pct = data["battery"].get("level", 100)
                    if pct <= 15:
                        payload["event"] = f"⚠ Low battery: {pct}%"
                    db.log_sensor(device_id, "battery", data["battery"])

                # ── Audio level ───────────────────────────────────────────────
                if "audio_level" in data:
                    payload["audio_level"] = data["audio_level"]

                # ── Photo ─────────────────────────────────────────────────────
                if "photo_base64" in data:
                    payload["photo_base64"] = data["photo_base64"]
                    payload["event"] = "Photo received"
                    db.log_event(device_id, "photo", {})

                socketio.emit("update_dashboard", payload)

            time.sleep(0.05)

    t = threading.Thread(target=run, daemon=True)
    t.start()