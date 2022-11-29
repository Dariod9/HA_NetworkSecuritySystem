# @Author: Dário Matos
# @Date:   2022-03-29 15:44:14
# @Email:  dario.matos@ua.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Dário Matos
# @Last Modified time: 2022-10-11 15:05:07
import json
from threading import Thread
from fastapi import FastAPI
import uvicorn
import conn

app = FastAPI()

connection = conn.HASystem()
daemon = Thread(target=connection.run, daemon=True, name="System")
daemon.start()
print("Começou")


@app.get("/devices")
def devices():
    slots = connection.get_equipment()
    a = dict()
    print(slots)
    if slots:
        for slot in slots:
            slot_info = dict()

            if "FW" in slot.name:
                slot_info["State"] = "Up" if slot.up else "False"
                slot_info["Management IP"] = slot.ip
                slot_info["Internal Interfaces"] = slot.interfaces_inside
                slot_info["External Interfaces"] = slot.interfaces_outside
                slot_info["Delayed Configs"] = slot.delayed_configs
            else:
                slot_info["State"] = "Up" if slot.up else "False"
                slot_info["Management IP"] = slot.ip
                slot_info["Zone"] = slot.zone
                slot_info["Interfaces"] = slot.interfaces
                slot_info["Delayed Configs"] = slot.delayed_configs

            a[slot.name] = slot_info

        json_object = json.dumps(a, indent=4)
        # print(json_object)

        return json.loads(json_object)
    else:
        return "No available equipment"


@app.get("/configure/{device_name}")
def device_configure(device_name: str):
    return connection.configure_device(device_name)


@app.get("/connections")
def connections():
    return connection.check_all_connections()


@app.get("/connections/{device_name}")
def device_connections(device_name: str):
    return connection.check_one_connections(device_name)


@app.get("/status")
def status():
    return connection.get_all_equipment_stats()


@app.get("/status/{device_name}")
def device_status(device_name: str):
    return connection.get_equipment_stats(device_name)


@app.get("/{device_name}")
def device(device_name: str):
    return connection.get_equipment_stats(device_name)


@app.post("/block/{ip}/")
def all_block_ip(ip: str):
    return connection.block_ip(None, ip, 0)


@app.post("/block/{ip}/{port}")
def all_block_ip_port(ip: str, port: str):
    return connection.block_ip(None, port)


@app.post("/{zone}/block/{ip}/")
def block_ip(zone: str, ip: str):
    return connection.block_ip(zone, ip, 0)


@app.post("/{zone}/block/{ip}/{port}")
def block_ip_port(zone: str, ip: str, port: str):
    return connection.block_ip(zone, ip, port)


@app.post("/allow/{ip}/")
def all_allow_ip(ip: str):
    return connection.allow_ip(None, ip, 0)


@app.post("/allow/{ip}/{port}")
def all_allow_ip_port(ip: str, port: str):
    return connection.allow_ip(None, port)


@app.post("/{zone}/allow/{ip}/")
def allow_ip(zone: str, ip: str):
    return connection.allow_ip(zone, ip, 0)


@app.post("/{zone}/allow/{ip}/{port}")
def allow_ip_port(zone: str, ip: str, port: str):
    return connection.allow_ip(zone, ip, port)


if __name__ == "__main__":
    # os.system('python3 conn.py')
    uvicorn.run(app, host="0.0.0.0", port=8000)
