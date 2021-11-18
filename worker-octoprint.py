import setproctitle
import os
import pprint
import time
import socketio
import argparse
from qclient import job_get, gcode_get, update_task, update_message, printerconfig_get

from octorest import OctoRest

sio = socketio.Client(logger=False, engineio_logger=False)

shared = {
    "running": True,
    "svcommand": "",
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
    update_message(shared, printer, sio, message)


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

    opclient = None
    shared["config"] = printerconfig_get(master, port, printer)
    url = shared["config"].get("url")
    apikey = shared["config"].get("apikey")
    ptype = shared["config"].get("type")
    if ptype != "octoprint":
        print(f"wrong printer type '{ptype}' != 'octoprint'")
        clientExit()

    if url and apikey:
        print("config: ", url, apikey, flush=True)
        try:
            opclient = OctoRest(url=url, apikey=apikey)
            print("Version:", opclient.version["text"])
        except Exception as e:
            print("can not connect to octoprint:", e, flush=True)
            clientExit()

    while shared["running"]:
        if shared["svcommand"]:
            cmd = shared["svcommand"]
            shared["svcommand"] = ""
            if cmd == "KILL":
                print("execute command: ", cmd)

        job = job_get(master, port, shared["active_job"])
        if job:
            pprint.pprint(job)

            print(job["filename"], flush=True)
            shared["mode"] = "INIT"
            shared["status"]["status"] = shared["mode"]

            duration = round(job.get("estimatedPrintTime") or 0)
            shared["status"]["duration"] = duration
            gcode = gcode_get(master, port, job["jobId"])

            gfile = "/tmp/queued-printing.gcode"
            open(gfile, "wb").write(gcode)
            res = opclient.upload(gfile, location="local", select=True, print=True)
            os.remove(gfile)

            print(res)
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

            while shared["running"]:

                print("get printer")
                octostatus = opclient.printer()
                hotend = octostatus.get("temperature", {}).get("tool0", {})
                bed = octostatus.get("temperature", {}).get("bed", {})
                shared["status"]["hotend"] = round(hotend.get("actual") or 0)
                shared["status"]["hotend_set"] = round(hotend.get("target") or 0)
                shared["status"]["bed"] = round(bed.get("actual") or 0)
                shared["status"]["bed_set"] = round(bed.get("target") or 0)
                shared["mode"] = (
                    octostatus.get("state", {}).get("text", "UNKNOWN").upper()
                )
                shared["status"]["status"] = shared["mode"]

                active_job = {
                    "jobId": job.get("jobId", ""),
                    "traceId": job.get("traceId", ""),
                    "status": shared["mode"],
                }
                shared["status"]["active"] = active_job

                print(shared["status"])
                time.sleep(1)

                print("get job")
                jobinfo = opclient.job_info()
                progress = jobinfo.get("progress", {})
                shared["status"]["percent"] = round(progress.get("completion") or 0)
                shared["status"]["time"] = round((progress.get("printTime") or 0) / 60)
                shared["status"]["remaining"] = round(
                    (progress.get("printTimeLeft") or 0) / 60
                )
                shared["status"]["duration"] = duration
                print(shared["status"])
                time.sleep(1)

                if shared["mode"] == "OPERATIONAL":
                    break

            shared["mode"] = "FINISHED"
            shared["status"]["status"] = shared["mode"]
            shared["status"]["percent"] = 100
            shared["active_job"] = {
                "jobId": job.get("jobId", ""),
                "traceId": job.get("traceId", ""),
                "status": shared["mode"],
            }
            shared["status"]["active"] = shared["active_job"]

            time.sleep(2)

            shared["active_job"] = {}
            shared["status"]["active"] = shared["active_job"]

        else:

            octostatus = opclient.printer()

            hotend = octostatus.get("temperature", {}).get("tool0", {})
            bed = octostatus.get("temperature", {}).get("bed", {})
            shared["status"]["hotend"] = round(hotend.get("actual") or 0)
            shared["status"]["hotend_set"] = round(hotend.get("target") or 0)
            shared["status"]["bed"] = round(bed.get("actual") or 0)
            shared["status"]["bed_set"] = round(bed.get("target") or 0)

            shared["mode"] = octostatus.get("state", {}).get("text", "UNKNOWN").upper()
            if shared["mode"] == "OPERATIONAL":
                shared["mode"] = "STANDBY"
            shared["status"]["status"] = shared["mode"]

            shared["active_job"] = {}
            shared["status"]["active"] = shared["active_job"]

            print(shared["status"])

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
