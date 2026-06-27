"""System info + IP geolocation."""

import json
import os
import platform

from . import tool
from ._http import http_json


@tool(
    description="Get system info: OS, CPU, memory usage.",
    parameters={"type": "object", "properties": {}},
)
def system_info() -> str:
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:
        import shutil
        du = shutil.disk_usage("/")
        info["disk_free_gb"] = round(du.free / 1e9, 1)
    except Exception:
        pass
    return json.dumps(info, indent=2)


@tool(
    description="Get this machine's public IP address and approximate location.",
    parameters={"type": "object", "properties": {}},
)
def my_ip() -> str:
    try:
        d = http_json("https://ipapi.co/json/")
        return (f"IP {d.get('ip')} — {d.get('city')}, {d.get('region')}, "
                f"{d.get('country_name')} ({d.get('org')})")
    except Exception as e:
        return f"IP lookup failed: {e}"
