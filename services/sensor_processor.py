from collections import deque

class SensorProcessor:
    def __init__(self):
        self.history = {}

    def process(self, device_id, acc):
        x, y, z = acc["x"], acc["y"], acc["z"]
        magnitude = (x**2 + y**2 + z**2) ** 0.5

        if device_id not in self.history:
            self.history[device_id] = deque(maxlen=20)

        self.history[device_id].append(magnitude)

        # classification
        if magnitude < 2:
            state = "Idle"
        elif magnitude < 10:
            state = "Normal"
        else:
            state = "High Activity"

        values = list(self.history[device_id])
        avg = sum(values) / len(values)
        peak = max(values)

        return {
            "x": x,
            "y": y,
            "z": z,
            "magnitude": round(magnitude, 2),
            "state": state,
            "avg": round(avg, 2),
            "peak": round(peak, 2)
        }