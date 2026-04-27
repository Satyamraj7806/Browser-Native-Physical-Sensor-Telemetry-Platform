# services/ingestion_service.py
from workers.sensor_worker import enqueue

class IngestionService:
    KNOWN_KEYS = {"accelerometer", "gps", "battery", "audio_level", "photo_base64", "fall_detected"}

    def ingest(self, data: dict):
        if not isinstance(data, dict):
            return
        if not data.get("device_id"):
            return
        # Pass through any known sensor key
        if not (self.KNOWN_KEYS & set(data.keys())):
            return
        enqueue(data)