from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from core.device_manager import DeviceManager
from services.ingestion_service import IngestionService
from services.command_service import CommandService
from workers.sensor_worker import start_worker
from api.routes import register_routes

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*")
device_manager = DeviceManager()
ingestion = IngestionService()
command_service = CommandService()

# start worker
start_worker(socketio, device_manager)
register_routes(app, device_manager)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/client")
def client():
    return render_template("client.html")

@socketio.on("register")
def handle_register(data):
    device_id = data.get("device_id") or f"phone-{request.sid[:4]}"
    device_manager.register(device_id, request.sid)
    emit("registered", {"device_id": device_id})

@socketio.on("sensor_data")
def handle_sensor(data):
    ingestion.ingest(data)

@socketio.on("send_command")
def handle_command(data):
    valid, error = command_service.validate(data)
    if not valid:
        emit("error", {"message": error})
        return

    sid = device_manager.get_sid(data["device_id"])
    if sid:
        socketio.emit("command", data, to=sid)


# After
socketio.run(app, host="0.0.0.0", port=5000, debug=True,
             ssl_context="adhoc")   # generates a temporary self-signed cert
