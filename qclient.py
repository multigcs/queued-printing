import json
import time
import urllib.request


def job_get(master, port, active):
    job = {}
    if active:
        req = urllib.request.urlopen(
            f"http://{master}:{port}/jobdata?job={active['jobId']}"
        )
        job = json.loads(req.read())
        job["jobId"] = active["jobId"]
        job["traceId"] = active["traceId"]
    return job


def printerconfig_get(master, port, printerId):
    req = urllib.request.urlopen(
        f"http://{master}:{port}/printerconfig?printer={printerId}"
    )
    printerConfig = json.loads(req.read())
    return printerConfig


def gcode_get(master, port, jobid):
    url = f"http://{master}:{port}/gcode?job={jobid}"
    print("gcode-url:", url, flush=True)
    req = urllib.request.urlopen(url)
    gcode = req.read()
    return gcode


def update_task(shared, printer, sio):
    last = time.time()
    while shared["running"]:

        try:
            # force status update every 10s
            if time.time() - last >= 10:
                last = time.time()
                shared["status"]["status"] = shared["mode"]
                shared["status"]["active"] = shared["active_job"]

            if shared["status"] or shared["errors"]:
                status_new = shared["status"].copy()
                shared["status"] = {}

                if shared["errors"]:
                    status_new["errors"] = shared["errors"]
                    shared["errors"] = {}

                if "next" in status_new:
                    del status_new["next"]

                sio.emit("update", {"printer": printer, "status": status_new})

        except Exception as e:
            print("ERROR in update task:", e, flush=True)
            shared["errors"][time.time()] = f"update task error: {e}"

        time.sleep(0.2)


def update_message(shared, printer, sio, message):

    try:
        if "printer" in message:
            printerName = message["printer"]

            if printerName != printer:
                print("not my printer: ", printerName, flush=True)
                return

            if "config" in message:
                printerConfig = message["config"]
                for key, value in printerConfig.items():
                    shared["config"][key] = value

            if "commands" in message:
                printerCommands = message["commands"]
                svcommand = printerCommands.get("svcommand", "")
                if svcommand:
                    shared["svcommand"] = svcommand

                # check for next job
                jobNext = printerCommands.get("next")
                if jobNext:
                    if not shared["active_job"]:
                        shared["active_job"] = {
                            "jobId": jobNext,
                            "traceId": f"{jobNext}-{time.time()}",
                            "status": shared["mode"],
                        }
                    else:
                        print("allready printing", flush=True)

                    print(
                        "update back ",
                        {
                            "printer": printer,
                            "status": {"next": "", "active": shared["active_job"]},
                        },
                        flush=True,
                    )
                    sio.emit(
                        "update",
                        {
                            "printer": printer,
                            "status": {"next": "", "active": shared["active_job"]},
                        },
                    )

            if "status" in message:
                printerStatus = message["status"]

                ready = printerStatus.get("ready") or 0
                shared["ready"] = ready

                # cleaning status data
                if "status" in printerStatus:
                    del printerStatus["status"]
                if "active" in printerStatus:
                    del printerStatus["active"]

    except Exception as e:
        print("send error:", e, flush=True)
        shared["errors"][time.time()] = "send update error"
