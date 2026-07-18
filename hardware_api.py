"""
Chhoti Don - Hardware Stats API
Real-time CPU, GPU, RAM monitoring backend.
Run: python hardware_api.py
Install: pip install flask flask-cors psutil pynvml
"""

from flask import Flask, jsonify
from flask_cors import CORS
import psutil
import datetime

app = Flask(__name__)
CORS(app)


def get_gpu_stats():
    """NVIDIA GPU stats via pynvml."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()

        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        return {
            "available": True,
            "name": name,
            "usage_percent": util.gpu,
            "memory_used_mb": round(mem.used / 1024**2),
            "memory_total_mb": round(mem.total / 1024**2),
            "memory_percent": round(mem.used / mem.total * 100, 1),
            "temperature_c": temp,
        }
    except Exception:
        return {
            "available": False,
            "name": "N/A",
            "usage_percent": 0,
            "memory_percent": 0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "temperature_c": 0,
        }


@app.route("/api/stats")
def get_stats():
    """Real-time hardware stats endpoint."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    cpu_count = psutil.cpu_count()

    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for key in ["coretemp", "k10temp", "cpu_thermal", "acpitz"]:
                if key in temps:
                    cpu_temp = round(temps[key][0].current, 1)
                    break
    except Exception:
        pass

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    gpu = get_gpu_stats()

    return jsonify({
        "status": "success",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "cpu": {
            "usage_percent": cpu_percent,
            "cores": cpu_count,
            "freq_mhz": round(cpu_freq.current) if cpu_freq else 0,
            "temperature_c": cpu_temp,
        },
        "ram": {
            "usage_percent": round(ram.percent, 1),
            "used_gb": round(ram.used / 1024**3, 1),
            "total_gb": round(ram.total / 1024**3, 1),
            "available_gb": round(ram.available / 1024**3, 1),
        },
        "gpu": gpu,
        "disk": {
            "usage_percent": round(disk.percent, 1),
            "used_gb": round(disk.used / 1024**3, 1),
            "total_gb": round(disk.total / 1024**3, 1),
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / 1024**2, 1),
            "bytes_recv_mb": round(net.bytes_recv / 1024**2, 1),
        },
    })


if __name__ == "__main__":
    print("=" * 45)
    print("  Chhoti Don Hardware API")
    print("  URL: http://localhost:5050/api/stats")
    print("=" * 45)
    app.run(host="0.0.0.0", port=5050, debug=False)
