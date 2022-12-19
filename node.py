import argparse
import glob
import subprocess
import time

import psutil
import setproctitle
import socketio

config = {}
svcommands = {}
deviceList = {}
errors = {}
running = True

sio = socketio.Client(logger=False, engineio_logger=False)


@sio.event
def connect():
    sio.emit("register", {"name": clientname, "type": "supervisor"})


@sio.event
def connect_error(data):
    global errors
    errors[time.time()] = "ws connection failed"


@sio.event
def disconnect():
    global errors
    errors[time.time()] = "ws disconnect"


@sio.event
def update(message):
    global svcommands
    global config
    global errors

    try:
        if "printer" in message:
            printerName = message["printer"]

            if printerName not in config:
                config[printerName] = {}

            if "config" in message:
                printerConfig = message["config"]
                for key, value in printerConfig.items():

                    if key not in ["port", "type"]:
                        continue

                    if config[printerName].get(key) != value:
                        config[printerName][key] = value

            if "commands" in message:
                printerCommands = message["commands"]
                cmd = printerCommands.get("svcommand", "")
                if cmd:
                    svcommands[printerName] = cmd

    except Exception as e:
        print("send error:", e, flush=True)
        errors[time.time()] = "send update error"


def supervisor_task():
    global deviceList
    global config

    while running:

        try:

            cpu_usage = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=False)
            mem_usage = psutil.virtual_memory().percent
            disk_free = psutil.disk_usage("/").free
            ips = {}
            for netDevice, netData in psutil.net_if_addrs().items():
                if netDevice != "lo":
                    ips[netDevice] = []
                    for cfg in netData:
                        if "." in cfg.address:
                            ips[netDevice].append(cfg.address)

            activeList = {}
            for devicePath in glob.glob("/dev/serial/by-path/*"):
                device = devicePath.split("/")[-1]
                if device not in deviceList:
                    print("found new device:", device, flush=True)
                    deviceList[device] = {"path": devicePath}
                activeList[device] = {"path": devicePath}

            for device in deviceList.copy():
                if device not in activeList:
                    print("remove device:", device, flush=True)
                    del deviceList[device]

            kconfigList = {}
            for dkconfigPath in glob.glob("klipper/config/*.cfg"):
                kconfigName = dkconfigPath.split("/")[-1].replace(".cfg", "")
                kconfigList[kconfigName] = {"path": dkconfigPath}

            sio.emit(
                "update",
                {
                    "kconfigs": kconfigList,
                    "devices": deviceList,
                    "system": {
                        "cpucount": cpu_count,
                        "cpuusage": cpu_usage,
                        "memusage": mem_usage,
                        "diskfree": disk_free,
                        "ips": ips,
                    },
                },
            )

            for printer, printerConfig in config.items():
                procName = f"worker-{printer}"
                devicePath = printerConfig.get("port", "")
                deviceName = devicePath.split("/")[-1]
                ptype = printerConfig.get("type", "")

                if svcommands.get(printer) == "KILL":
                    print(f"{printer}: killing worker by command", flush=True)
                    svcommands[printer] = ""

                    for proc in psutil.process_iter():
                        if proc.name() == procName:
                            proc.kill()

                if deviceName in deviceList or ptype in [
                    "klipperrun",
                    "octoprint",
                    "simulator",
                ]:
                    found = False
                    for proc in psutil.process_iter():
                        if proc.name() == procName:
                            found = True

                    if not found:
                        sio.emit(
                            "update",
                            {"printer": printer, "status": {"status": "OFFLINE"}},
                        )
                        cmd = f"nohup python3 worker-{ptype}.py -u '{uri}' -n '{clientname}' -p '{printer}' > '/tmp/log_{printer}.log' 2>&1 &"
                        print(f"{printer}: try to start worker: {cmd}", flush=True)
                        subprocess.run(cmd, shell=True)

                else:
                    sio.emit(
                        "update",
                        {"printer": printer, "status": {"status": "OFFLINE"}},
                    )

                    found = False
                    for proc in psutil.process_iter():
                        if proc.name() == procName:
                            found = True

                    if found:
                        print(
                            f"{printer}: stopping worker... TODO: double check",
                            flush=True,
                        )
                        # proc.kill()

        except Exception as e:
            print("send error:", e, flush=True)
            errors[time.time()] = "supervisor error"

        time.sleep(3)


if __name__ == "__main__":
    print("starting supervisor", flush=True)

    parser = argparse.ArgumentParser(description="gCode-Sender")
    parser.add_argument("-n", "--node", help="Node-Name", required=True)
    parser.add_argument("-u", "--uri", help="Websocket-URI", required=True)
    args = parser.parse_args()

    clientname = args.node
    uri = args.uri

    setproctitle.setproctitle("qp-supervisor")

    sio.connect(uri)

    task1 = sio.start_background_task(supervisor_task)

    try:
        sio.wait()
    except KeyboardInterrupt:
        running = False
        sio.disconnect()
