# api/routes.py
import csv
import io
import time
from flask import jsonify, request, Response
from services.db_services import DBService

db = DBService()

def register_routes(app, device_manager):

    @app.route("/devices")
    def list_devices():
        return jsonify(device_manager.list_devices())

    @app.route("/history/<device_id>/<sensor_type>")
    def get_history(device_id, sensor_type):
        limit = int(request.args.get("limit", 100))
        rows = db.recent_sensors(device_id, sensor_type, limit)
        return jsonify(rows)

    @app.route("/events/<device_id>")
    def get_events(device_id):
        limit = int(request.args.get("limit", 50))
        rows = db.recent_events(device_id, limit)
        return jsonify(rows)

    @app.route("/export/<device_id>/<sensor_type>")
    def export_csv(device_id, sensor_type):
        """Download sensor history as CSV."""
        rows = db.recent_sensors(device_id, sensor_type, limit=10000)
        if not rows:
            return "No data", 404

        out = io.StringIO()
        # Flatten first row to get column names
        first = rows[0]["data"]
        fields = list(first.keys())
        writer = csv.DictWriter(out, fieldnames=["ts"] + fields)
        writer.writeheader()
        for r in rows:
            row = {"ts": r["ts"]}
            row.update({k: r["data"].get(k, "") for k in fields})
            writer.writerow(row)

        return Response(
            out.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={device_id}_{sensor_type}.csv"}
        )