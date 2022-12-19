import argparse
import pprint
import re
import subprocess
import time

import psutil
import serial
import setproctitle
import socketio

from qclient import gcode_get, job_get, printerconfig_get, update_message, update_task

regex_start = re.compile("G[01] .*E[1-9]{1,10}")

sio = socketio.Client(logger=False, engineio_logger=False)

shared = {
    "running": True,
    "svcommand": "",
    "ready": 0,
    "config": {},
    "errors": {},
    "caps": {},
    "active_job": "",
    "status_start": 0,
    "mode": "STARTUP",
    "status": {},
}


def msg_decode(msg):
    global shared

    if not isinstance(msg, str):
        msg = msg.decode()

    if msg.strip() == "ok":
        return

    if msg.startswith("ok "):
        msg = msg[3:]

    print(f" <- {msg.strip()}")

    if msg.startswith("TT::"):
        last = ""
        for part in msg.split():
            if part.startswith("TT::"):
                shared["status"]["hotend"] = part.split(":")[2].split(".")[0]
                last = "hotend"
            elif part.startswith("BB::"):
                shared["status"]["bed"] = part.split(":")[2].split(".")[0]
                last = "bed"
            elif part.startswith("//"):
                shared["status"][f"{last}_set"] = part.split("/")[2].split(".")[0]

    elif msg.startswith("T:") or msg.startswith("B:") or msg.startswith("T0:"):
        last = ""
        for part in msg.split():
            if part.startswith("T:"):
                shared["status"]["hotend"] = part.split(":")[1].split(".")[0]
                last = "hotend"
            elif part.startswith("T0:"):
                shared["status"]["hotend"] = part.split(":")[1].split(".")[0]
                last = "hotend"
            elif part.startswith("B:"):
                shared["status"]["bed"] = part.split(":")[1].split(".")[0]
                last = "bed"
            elif part.startswith("/"):
                shared["status"][f"{last}_set"] = part.split("/")[1].split(".")[0]

    elif msg.startswith("X:"):
        for part in msg.split():
            if ":" in part:
                axis, pos = part.split(":")
                shared["status"][f"pos_{axis.lower()}"] = pos

            elif part == "Count":
                break

    elif msg.startswith("FIRMWARE"):
        shared["status"]["firmware"] = msg

    elif msg.startswith("Error:") or msg.startswith("// ") or msg.startswith("!! "):
        shared["errors"][time.time()] = msg
        if msg.startswith("// action:cancel"):
            clientExit()

    #        elif msg.startswith("// Printer is not ready") or msg.startswith(
    #            "// Error configuring printer"
    #        ):
    #            shared["running"] = False
    #            sio.disconnect()
    #            exit(0)

    elif msg.startswith("Cap:"):
        parts = msg.split(":")
        cap = parts[1]
        val = parts[2]
        shared["caps"][cap] = val
        shared["status"]["cap"] = shared["caps"]

    print(".", flush=True)


def send(cmd):
    if isinstance(cmd, str):
        cmd = cmd.encode()
    s.write(cmd + b"\n")


def sendReceive(cmd):
    global shared

    if isinstance(cmd, str):
        cmd = cmd.encode()

    send(cmd)
    msg = s.readline().decode()
    msg_decode(msg.strip())

    timeout = time.time()
    while shared["running"] and not msg.strip().startswith("ok"):

        if shared["svcommand"]:
            cmd = shared["svcommand"]
            shared["svcommand"] = ""
            if cmd == "KILL":
                print("execute command (in wait): ", cmd)

                # Emergency Stop
                # send("M112")

                # set hostend temp to 0
                send("M104 S0")

                # set bad temp to 0
                send("M140 S0")

                # set bad temp to 0
                send("M18")

                clientExit()

        print("wait", flush=True)
        if (time.time() - timeout) > 600:
            print(f"#### TIMEOUT: {time.time() - timeout} ####", flush=True)
            break

        msg = s.readline().decode(errors="ignore")
        msg_decode(msg.strip())

        if int(time.time() - timeout + 1) % 2 == 0:
            if shared["status_start"]:
                shared["status"]["time"] = int(time.time() - shared["status_start"])


@sio.event
def connect():
    sio.emit("register", {"name": clientname, "printer": printer, "type": "worker"})


@sio.event
def connect_error(data):
    global shared
    shared["errors"][time.time()] = "ws connection failed"


@sio.event
def disconnect():
    global shared
    shared["errors"][time.time()] = "ws disconnect"


@sio.event
def update(message):
    global shared
    update_message(shared, printer, sio, message)


def waitActions():
    if shared["svcommand"]:
        cmd = shared["svcommand"]
        shared["svcommand"] = ""
        if cmd == "KILL":
            print("execute command (in main): ", cmd)

            # Emergency Stop
            # send("M112")

            # set hostend temp to 0
            send("M104 S0")

            # set bad temp to 0
            send("M140 S0")

            # set bad temp to 0
            send("M18")

            clientExit()

    sendReceive(f"M117 {shared['config'].get('name')}")
    sendReceive("M115")
    sendReceive("M105")


def clientExit():
    global shared
    shared["running"] = False
    sio.disconnect()
    time.sleep(2)
    exit(0)


def task_main():
    global s
    global shared

    shared["active_job"] = {}
    shared["status"]["active"] = shared["active_job"]
    shared["status"]["next"] = ""

    shared["config"] = printerconfig_get(master, port, printer)
    ptype = shared["config"].get("type")
    kconfig = shared["config"].get("kconfig")
    if ptype and ptype not in ["klipperrun"]:
        print(f"wrong printer type '{ptype}' != 'klipperrun'")
        clientExit()

    if kconfig:
        print("config: ", kconfig, flush=True)

        # checking if klipper (klippy.py) is running
        found = False
        for proc in psutil.process_iter():
            cmdline = proc.cmdline()
            if cmdline and len(cmdline) > 3:
                if (
                    cmdline[0] == "python3"
                    and cmdline[1].endswith("klippy.py")
                    and cmdline[3] == f"/tmp/klippy-{printer}"
                ):
                    found = True
                    print(cmdline)

        # if not, starting klipper (klippy.py)
        if not found:
            klipper_cmd = (
                f"nohup python3 klipper/klippy/klippy.py  -I '/tmp/klippy-{printer}' -l '/tmp/log_klipper_{printer}.log' '{kconfig}' > /tmp/log_klipper_{printer} 2>&1 &",
            )
            print(klipper_cmd)
            subprocess.run(
                klipper_cmd,
                shell=True,
            )
            time.sleep(10)

        # connecting to klipper (klippy.py) via virtual serial-port
        try:
            s = serial.Serial(f"/tmp/klippy-{printer}", 115200, timeout=2)
            s.write(b"\r\n\r\n")
        except Exception as e:
            print("can not open to serial:", e, flush=True)
            clientExit()

    time.sleep(2)
    s.flushInput()

    # set hostend temp to 0
    sendReceive("M104 S0")

    # set bad temp to 0
    sendReceive("M140 S0")

    # get firmware info
    sendReceive("M115")

    # get settings
    sendReceive("M503")

    # send N commands without waiting, so we have N commands in the buffer
    cmdbuffer = int(shared["config"].get("cmdbuffer", 0))
    for _n in [range(0, cmdbuffer)]:
        send("G0")

    while shared["running"]:

        waitActions()

        job = job_get(master, port, shared["active_job"])
        if job:
            pprint.pprint(job)

            print(job["filename"], flush=True)
            shared["mode"] = "INIT"
            shared["status"]["status"] = shared["mode"]

            duration = round(job.get("estimatedPrintTime") or 0)
            shared["status"]["duration"] = duration
            gcode = gcode_get(master, port, job["jobId"])

            # init printing
            shared["status_start"] = time.time()
            shared["status"]["start"] = shared["status_start"]
            shared["status"]["time"] = 0
            s.write(b"\r\n\r\n")
            time.sleep(2)
            s.flushInput()

            # get firmware info
            sendReceive("M115")

            # get settings
            sendReceive("M503")

            # start printing
            shared["mode"] = "HEATING"
            shared["status"]["status"] = shared["mode"]
            shared["active_job"] = {
                "jobId": job.get("jobId", ""),
                "traceId": job.get("traceId", ""),
                "status": shared["mode"],
            }
            shared["status"]["active"] = shared["active_job"]

            sendReceive(f"M117 {job['filename']}")

            heating = True

            lines = gcode.split(b"\n")
            lines_total = len(lines)
            line_num = 0
            last_msg = time.time()
            for line_num, line in enumerate(lines):

                if shared["svcommand"]:
                    cmd = shared["svcommand"]
                    shared["svcommand"] = ""
                    if cmd == "KILL":
                        print("execute command (in printing): ", cmd)

                        # Emergency Stop
                        # send("M112")

                        # set hostend temp to 0
                        send("M104 S0")

                        # set bad temp to 0
                        send("M140 S0")

                        # set bad temp to 0
                        send("M18")

                        clientExit()

                sline = line.split(b";")[0].strip()
                if sline:
                    print(sline)

                    if heating and regex_start.match(line.decode()):
                        heating = False
                        shared["mode"] = "PRINTING"
                        shared["active_job"] = {
                            "jobId": job.get("jobId", ""),
                            "traceId": job.get("traceId", ""),
                            "status": shared["mode"],
                        }
                        shared["status"]["active"] = shared["active_job"]
                        shared["status"]["status"] = shared["mode"]
                        shared["status_start"] = time.time()
                        shared["status"]["start"] = shared["status_start"]

                    sendReceive(sline)

                    if time.time() - last_msg >= 10:
                        last_msg = time.time()
                        status_time = int(time.time() - shared["status_start"])
                        if duration:
                            percent = round(status_time / duration * 100)
                        else:
                            percent = round(line_num / lines_total * 100)
                        shared["status"]["time"] = status_time
                        shared["status"]["percent"] = percent
                        if duration:
                            remaining = round((duration - status_time) / 60)
                            shared["status"]["remaining"] = remaining
                            msg_cmd = f"M117 {remaining} minutes"
                            prg_cmd = f"M73 P{percent} R{remaining}"
                        else:
                            shared["status"]["remaining"] = ""
                            prg_cmd = f"M73 P{percent}"
                            msg_cmd = f"M117 {percent}%"

                        sendReceive(msg_cmd)
                        sendReceive(prg_cmd)
                        sendReceive("M105")

                        print("", flush=True)

            shared["mode"] = "FINISHED"
            shared["status"]["status"] = shared["mode"]
            shared["status"]["percent"] = 100
            shared["active_job"] = {
                "jobId": job.get("jobId", ""),
                "traceId": job.get("traceId", ""),
                "status": shared["mode"],
            }
            shared["status"]["active"] = shared["active_job"]

            while not shared["ready"]:
                print("waiting for printer set to ready", flush=True)
                waitActions()
                time.sleep(1)

            shared["active_job"] = {}
            shared["status"]["active"] = shared["active_job"]

        else:
            shared["mode"] = "STANDBY"
            shared["status"]["status"] = shared["mode"]
            shared["active_job"] = {}
            shared["status"]["active"] = shared["active_job"]
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dummy-Printer")
    parser.add_argument("-p", "--printer", help="Printer-Name", required=True)
    parser.add_argument("-n", "--node", help="Node-Name", required=True)
    parser.add_argument("-u", "--uri", help="Websocket-URI", required=True)
    args = parser.parse_args()

    clientname = args.node
    printer = args.printer
    uri = args.uri

    uriParts = uri.split(":")
    master = uriParts[1].strip("/")
    port = uriParts[2]

    setproctitle.setproctitle(f"worker-{printer}")

    sio.connect(uri)

    task1 = sio.start_background_task(task_main)
    task2 = sio.start_background_task(update_task, shared, printer, sio)

    try:
        sio.wait()
    except KeyboardInterrupt:
        shared["running"] = False
        sio.disconnect()
