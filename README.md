# Browser-Native Physical Sensor Telemetry Platform

A real-time, multi-node telemetry system that turns any modern smartphone into a wireless sensor unit — no native app, no installation, no pairing. The browser alone streams accelerometer, GPS, battery, and audio data over WebSocket to a central dashboard that performs live statistical analysis, frequency-domain signal processing, and geospatial tracking.

---

## What makes this different

Most IoT projects require dedicated hardware, flashed firmware, or custom mobile apps. This system uses the Web APIs already present in every modern browser — `DeviceMotion`, `Geolocation`, `Battery`, `AudioContext`, `MediaDevices` — turning any phone into a deployable sensor node the moment it opens a URL. The backend is lightweight Python; the signal processing runs in JavaScript with no external libraries for the core math.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Phone (Browser)                     │
│  DeviceMotion  Geolocation  Battery  MediaDevices        │
│       └──────────────┬──────────────────┘                │
│                 WebSocket (Socket.IO)                    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                  Flask-SocketIO Server                   │
│                                                          │
│  IngestionService  →  SensorWorker (20 Hz drain loop)   │
│         │                    │                           │
│  CommandService        SensorProcessor                   │
│         │                    │                           │
│   DeviceManager          DBService (SQLite)              │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│              Dashboard (Browser)                         │
│  Leaflet Map  |  Chart.js  |  DFT Engine  |  Multi-node │
└──────────────────────────────────────────────────────────┘
```

---

## Features

### Sensor Acquisition (Phone Side)

**Accelerometer streaming**
Reads `accelerationIncludingGravity` from the `DeviceMotion` API at the device's native rate (typically 50–60 Hz). Streams X, Y, Z axes to the server continuously. On iOS 13+, runtime permission is requested before activation.

**GPS tracking**
Uses `navigator.geolocation.watchPosition()` with `enableHighAccuracy: true`. Each position fix includes latitude, longitude, accuracy radius, and speed. Updates are pushed to the server immediately on each fix and logged to SQLite with a Unix timestamp.

**Battery monitoring**
Queries the `Battery Status API` (`navigator.getBattery()`). Reports level percentage and charging state. Listens to `levelchange` and `chargingchange` events so the dashboard updates without polling. The server triggers a low-battery event at or below 15%.

**Ambient audio level**
Opens the microphone via `getUserMedia` with audio-only constraints. Routes the stream through a Web `AudioContext` analyser node. Computes the RMS (root mean square) amplitude of each FFT frame — a measure of loudness with no audio ever recorded or transmitted. Sends normalised level and percentage to the server at approximately 6 Hz.

**Camera capture**
On command, opens the rear camera via `getUserMedia`, waits for `loadedmetadata` and a 350 ms stabilisation window, draws a frame to a canvas, and transmits it as a base64-encoded JPEG. The stream is immediately released after capture.

**Torch control**
Acquires the rear camera stream and applies `{ advanced: [{ torch: true/false }] }` constraints via `applyConstraints()`. Gracefully falls back with an informative message on devices where the `torch` capability is not advertised.

**Vibration**
Uses `navigator.vibrate()` with a pattern `[200, 80, 200]` (two pulses). Simultaneously triggers a CSS shake animation as a visual confirmation.

### Fall Detection

A two-stage algorithm running entirely on the phone:

1. **Impact stage** — if the resultant magnitude `sqrt(x² + y² + z²)` exceeds 22 m/s², a spike timestamp is recorded.
2. **Stillness stage** — if within 800 ms of the spike the magnitude drops below 3 m/s² (device lying flat), a fall event is declared.

On detection: the phone vibrates three times, a red banner appears on the phone UI, and a `fall_detected` payload is emitted to the server. The dashboard displays a full-width alert banner and logs the event to SQLite. A 5-second cooldown prevents duplicate triggers.

### Signal Analysis (Dashboard Side)

**Time-domain chart**
Rolling 60-point line chart (Chart.js) showing magnitude and individual X/Y/Z axes. Updates at sensor rate with `animation: false` for zero-lag rendering.

**Discrete Fourier Transform (frequency spectrum)**
A DFT is computed in JavaScript directly on the incoming magnitude stream — no library, no WebAssembly. Implementation:

- Maintains a 128-sample rolling buffer of magnitude values
- Subtracts the signal mean to remove the DC/gravity component
- Computes the DFT: for each frequency bin `k`, evaluates `Σ signal[n] · cos(2πkn/N)` and the imaginary component via sine, yielding amplitude at that frequency
- Converts amplitude to decibels (`20 · log₁₀(amplitude)`) for display
- At a nominal 50 Hz sample rate with N=128, this resolves 0 to 25 Hz — the full range of human motion

**Motion classification from dominant frequency**

| Frequency Range | Classified Motion |
|---|---|
| 0 – 0.5 Hz | Static |
| 0.5 – 2.0 Hz | Walking |
| 2.0 – 4.0 Hz | Running / Jogging |
| > 4.0 Hz | Vibration / Vehicle |

**Movement state label**
Server-side classification using magnitude thresholds: Idle (< 2 m/s²), Normal (2–10 m/s²), High Activity (> 10 m/s²). State transitions are detected and emitted as named events.

### Geospatial Tracking

Live GPS map powered by Leaflet.js with OpenStreetMap tiles. Each device gets its own `circleMarker` and a polyline trail preserving the last 50 GPS fixes. The map pans to follow the currently selected device. Lat/lng, speed (km/h), and accuracy (m) are displayed below the map. All fixes are persisted to SQLite.

### Multi-Device Panel

Any number of phones can connect simultaneously. The sidebar lists all active nodes with per-device state badges (Idle / Normal / High Activity). Clicking a device focuses all dashboard panels on that node's data stream. The first device to connect is auto-selected. Commands can be sent to any selected device independently.

### Data Persistence (SQLite)

All sensor readings and discrete events are written to `sensor_dashboard.db` via a thread-safe WAL-mode SQLite connection. Two tables:

- `sensor_logs` — timestamped JSON readings per device per sensor type
- `event_logs` — discrete events (fall detected, photo received, state change, low battery)

### HTTP API

| Endpoint | Description |
|---|---|
| `GET /devices` | List all connected device IDs |
| `GET /history/<device_id>/<sensor_type>` | Recent sensor readings (JSON) |
| `GET /events/<device_id>` | Recent named events (JSON) |
| `GET /export/<device_id>/<sensor_type>` | Download readings as CSV |

---

## Stack

| Layer | Technology |
|---|---|
| Server | Python 3, Flask, Flask-SocketIO |
| Realtime transport | Socket.IO (WebSocket with polling fallback) |
| Persistence | SQLite 3 (WAL mode) |
| Dashboard UI | Vanilla JS, Chart.js 4, Leaflet.js 1.9 |
| Signal processing | Custom DFT — zero external dependencies |
| Sensor APIs | W3C DeviceMotion, Geolocation, Battery Status, Web Audio, MediaDevices |

---

## Project Structure

```
.
├── app.py                     # Flask app, Socket.IO event handlers
├── config.py
├── api/
│   └── routes.py              # REST endpoints (devices, history, export)
├── core/
│   └── device_manager.py      # Per-device state, SID registry, last-seen
├── models/
│   ├── device.py
│   └── sensor_data.py
├── services/
│   ├── ingestion_service.py   # Validates and enqueues incoming sensor data
│   ├── sensor_processor.py    # Magnitude, classification, rolling stats
│   ├── command_service.py     # Command validation
│   ├── db_service.py          # SQLite read/write (thread-safe)
│   └── rules_engine.py
├── workers/
│   └── sensor_worker.py       # 20 Hz drain loop, emits update_dashboard
├── templates/
│   ├── index.html             # Dashboard (map, FFT, multi-device, charts)
│   └── client.html            # Phone node UI (all sensor controls)
├── static/
│   ├── index.css
│   └── client.css
└── sensor_dashboard.db        # Auto-created on first run
```

---

## Setup

**Requirements**

```
Python >= 3.10
pip install flask flask-socketio pyopenssl
```

**Run**

```bash
python app.py
```

Default: `http://0.0.0.0:5000`

**HTTPS (required for camera, torch, and microphone on non-localhost)**

```bash
# Quick self-signed (browser will warn — tap Advanced > Proceed)
# In app.py, change the last line to:
socketio.run(app, host="0.0.0.0", port=5000, ssl_context="adhoc")
```

Or use `mkcert` for a trusted local certificate with no browser warning.

**Open on phone**

Navigate to `https://<your-local-ip>:5000/client` and tap **Start** to begin streaming.

---

## PSLP Syllabus Connections

This project is a direct applied implementation of the following topics from the PSLP curriculum:

| Syllabus Topic | Implementation |
|---|---|
| Random Variables | Each sensor axis (X, Y, Z) is a discrete-time random variable |
| Functions of Random Variables | Magnitude `sqrt(x²+y²+z²)` is a derived random variable |
| Normal Distribution | MEMS accelerometer noise follows a Gaussian distribution; threshold design assumes this |
| Poisson Distribution | Fall events and GPS fixes over time follow a Poisson arrival process |
| Point Estimation | Rolling 20-sample mean is a sample mean estimator; peak is the sample maximum |
| Central Limit Theorem | Justifies stability of rolling average as an estimator with N=20 |
| Frequency Distributions & Histograms | FFT spectrum is a frequency distribution of signal energy across bins |
| Numerical Summaries of Data | Average, peak, and magnitude computed per device in real time |
| Hypothesis Testing | Fall detection is a threshold test: H₀ = normal motion, H₁ = fall; threshold is the critical value |
| Logistic Regression | Motion state classification (categorical output from continuous magnitude input) |
| Time Sequence Plots | Time-domain chart is a live time series plot |
| Scatter Diagrams | X vs Y axis values can be plotted as a 2D scatter |
| Correlation | Covariance between axes analysable from logged SQLite data |

---

## Browser API Compatibility

| API | Chrome Android | Safari iOS | Firefox Android |
|---|---|---|---|
| DeviceMotion | Yes (permission prompt on some versions) | Yes (iOS 13+ requires permission) | Yes |
| Geolocation | Yes | Yes | Yes |
| Battery Status | Yes | No | Partial |
| Web Audio / getUserMedia | Yes (HTTPS only) | Yes (HTTPS only) | Yes (HTTPS only) |
| Torch via MediaTrack | Yes (device-dependent) | No | No |
| Vibration | Yes | No | Yes |

---

## Known Limitations

- Torch control is only available on Chrome for Android; Safari does not expose the torch capability through web APIs
- Battery Status API is not available on iOS Safari
- DeviceMotion on Android does not require a permission prompt in most browser versions; iOS 13+ does
- Camera and microphone require HTTPS on all non-localhost origins — running over plain HTTP on a local IP will result in `navigator.mediaDevices` being undefined
- The DFT is O(N²) — acceptable at N=128 but not suitable for larger FFT sizes in this implementation