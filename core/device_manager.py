# core/device_manager.py
import time

class DeviceManager:
    def __init__(self):
        self._devices = {}   # device_id → { sid, last_seen, state }

    def register(self, device_id: str, sid: str):
        self._devices[device_id] = {
            "sid":       sid,
            "last_seen": time.time(),
            "state":     None,
        }

    def get_sid(self, device_id: str):
        d = self._devices.get(device_id)
        return d["sid"] if d else None

    def touch(self, device_id: str):
        if device_id in self._devices:
            self._devices[device_id]["last_seen"] = time.time()
        else:
            # auto-create placeholder if device sends data before explicit register
            self._devices[device_id] = {
                "sid":       None,
                "last_seen": time.time(),
                "state":     None,
            }

    def seconds_since(self, device_id: str) -> float:
        d = self._devices.get(device_id)
        if not d:
            return -1
        return round(time.time() - d["last_seen"], 1)

    def get_state(self, device_id: str):
        d = self._devices.get(device_id)
        return d["state"] if d else None

    def set_state(self, device_id: str, state: str):
        if device_id in self._devices:
            self._devices[device_id]["state"] = state

    def list_devices(self):
        return list(self._devices.keys())