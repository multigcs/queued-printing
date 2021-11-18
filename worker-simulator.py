import setproctitle
import pprint
import time
import socketio
import argparse
from qclient import job_get, gcode_get, update_task, update_message, printerconfig_get

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
    print("update received")
    update_message(shared, printer, sio, message)


def waitActions():
    if shared["svcommand"]:
        cmd = shared["svcommand"]
        shared["svcommand"] = ""
        if cmd == "KILL":
            print("execute command (in main): ", cmd)
            clientExit()

    shared["status"]["hotend"] = 20
    shared["status"]["hotend_set"] = 0
    shared["status"]["bed"] = 20
    shared["status"]["bed_set"] = 0


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
    print("config:", shared["config"])

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
            print("gcode: ", gcode[:256])

            time.sleep(1)

            shared["mode"] = "HEATING"
            shared["status"]["status"] = shared["mode"]

            time.sleep(1)

            shared["mode"] = "PRINTING"
            shared["status"]["status"] = shared["mode"]
            shared["status"]["start"] = time.time()
            shared["active_job"] = {
                "jobId": job.get("jobId", ""),
                "traceId": job.get("traceId", ""),
                "status": shared["mode"],
            }
            shared["status"]["active"] = shared["active_job"]

            hotend = 0
            bed = 0
            while shared["running"]:

                if shared["svcommand"]:
                    cmd = shared["svcommand"]
                    shared["svcommand"] = ""
                    if cmd == "KILL":
                        print("execute command: ", cmd)
                        clientExit()

                shared["status"]["hotend"] = hotend
                shared["status"]["hotend_set"] = 205
                shared["status"]["bed"] = bed
                shared["status"]["bed_set"] = 70
                shared["status"]["percent"] = 50
                shared["status"]["time"] = 10
                shared["status"]["remaining"] = 10
                shared["status"]["duration"] = 20
                print(shared["status"])

                hotend += 2
                bed += 1

                if hotend >= 205:
                    break

                time.sleep(0.1)

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
