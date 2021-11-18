#!/usr/bin/env python3
"""

# What is Queued-Printing

it's a web-based 3d-printing-server to manage and monitor multiple 3d-printers

# How can i install it

## on Linux-System's

cd /usr/src/
git clone ....

## on an Raspberry-Pi

download and flash the image to sd-card


# How can i start it

python3 server.py


"""

import traceback
import copy
import psutil
import datetime
import uuid
import subprocess
import glob
import os
from shutil import copyfile, rmtree
import json
import time
from threading import Lock
from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    send_file,
    Response,
)
from flask_socketio import SocketIO
import socket
import urllib

import repetier
from gcode import gcode_analyze, gcode_thumbs, gcode_info

async_mode = None
thread = None
mpthread = None
thread_lock = Lock()

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

socketio = SocketIO(app)
socketio.init_app(app, cors_allowed_origins="*")

history_len = 20
history_interval = 5
multiserver_interval = 2
printer_interval = 3

shared = {
    "node": {},
    "job": {},
    "project": {},
    "activeProject": "",
    "client": {},
    "printerConfig": {},
    "printerStatus": {},
    "printerCommands": {},
    "multiprintserver": {},
}


if os.path.isfile("config/multiprintserver.json"):
    shared["multiprintserver"] = json.loads(
        open("config/multiprintserver.json", "r").read()
    )


filamentList = ["PLA", "PETG", "NYLON", "ABS", "TPU", "ASA"]

emptyPrinterConfig = {
    "name": "",
    "filament": "PLA",
    "filament_types": copy.deepcopy(filamentList),
    "groups": ["marlin-20x20"],
    "image": "generig.jpg",
    "node": "",
    "type": "unknown",
    "port": "",
    "baud": "115200",
    "cmdbuffer": 0,
}
emptyPrinterStatus = {
    "status": "UNKNOWN",
    "running": "0",
    "active": "",
    "ready": 0,
    "remaining": "0",
    "percent": "0",
    "bed": "0",
    "bed_set": "0",
    "bed_history": ["0"] * history_len,
    "bed_set_history": ["0"] * history_len,
    "hotend": "0",
    "hotend_set": "0",
    "hotend_history": ["0"] * history_len,
    "hotend_set_history": ["0"] * history_len,
}
emptyPrinterCommands = {"next": "", "svcommand": ""}


def multiprintserver_save(backup=True):
    """
    This function saves the multiprintserver configuration as a json file
    """
    print("saveing multiprintserver.json")
    if backup and os.path.isfile("config/multiprintserver.json"):
        copyfile(
            "config/multiprintserver.json",
            f"config/multiprintserver.json.{int(time.time())}",
        )
    open("config/multiprintserver.json", "w").write(
        json.dumps(shared["multiprintserver"], indent=4)
    )


def printers_save(backup=True):
    """
    This function saves the printer configuration as a json file
    """
    print("saveing printers.json")
    if backup and os.path.isfile("config/printer.json"):
        copyfile("config/printer.json", f"config/printer.json.{int(time.time())}")
    # filter out dynamic printers (from repetier-server)
    printerSave = {}
    for printerId, printerConfig in shared["printerConfig"].items():
        if printerConfig["type"] != "repetierserver":
            printerSave[printerId] = shared["printerConfig"][printerId]
    open("config/printer.json", "w").write(json.dumps(printerSave, indent=4))


def printers_reload():
    """
    This function (re)loads the printer configuration from a json file
    """
    global shared
    global multiserver_interval
    if os.path.isfile("config/printer.json"):
        printerConfigs = json.loads(open("config/printer.json", "r").read())
        for printerId, printerConfig in printerConfigs.items():
            shared["printerConfig"][printerId] = copy.deepcopy(emptyPrinterConfig)
            if printerId not in shared["printerCommands"]:
                shared["printerCommands"][printerId] = copy.deepcopy(
                    emptyPrinterCommands
                )
            if printerId not in shared["printerStatus"]:
                shared["printerStatus"][printerId] = copy.deepcopy(emptyPrinterStatus)

            for key, value in printerConfig.items():
                shared["printerConfig"][printerId][key] = value

    try:
        for printserverId, printserverData in shared["multiprintserver"].items():
            if (
                printserverData.get("active") == "1"
                and printserverData.get("type") == "repetierserver"
            ):
                url = printserverData["url"]
                apiKey = printserverData["apiKey"]
                if not apiKey:
                    apiKey = repetier.apikey_get(url)
                sprinters = repetier.printer_list(url, apiKey)
                if not sprinters:
                    continue
                sortedPrinters = sorted(sprinters, key=lambda item: item["name"])
                for sprinterData in sortedPrinters:
                    if sprinterData["online"] != 1:
                        continue

                    sprinterId = sprinterData["slug"]
                    pinfo = repetier.printer_info(url, apiKey, sprinterId)
                    if not pinfo:
                        continue
                    printerId = f"{apiKey}-{sprinterId}"

                    shared["printerConfig"][printerId] = copy.deepcopy(
                        emptyPrinterConfig
                    )
                    if printerId not in shared["printerCommands"]:
                        shared["printerCommands"][printerId] = copy.deepcopy(
                            emptyPrinterCommands
                        )
                    if printerId not in shared["printerStatus"]:
                        shared["printerStatus"][printerId] = copy.deepcopy(
                            emptyPrinterStatus
                        )

                    printerConfig = shared["printerConfig"][printerId]
                    printerStatus = shared["printerStatus"][printerId]
                    printerConfig[
                        "name"
                    ] = f"{sprinterId} on ({printserverData['name']})"
                    printerConfig["nameOrigin"] = sprinterId
                    printerConfig["apiKey"] = apiKey
                    printerConfig["url"] = url
                    printerConfig["type"] = "repetierserver"
                    printerStatus["active"] = ""
                    printerStatus["running"] = 1
                    printerStatus["ready"] = 1
                    printerStatus["status"] = "STANDBY"
                    printerStatus["hotend"] = round(pinfo["extruder"][0]["tempRead"])
                    printerStatus["hotend_set"] = round(pinfo["extruder"][0]["tempSet"])
                    printerStatus["bed"] = round(pinfo["heatedBeds"][0]["tempRead"])
                    printerStatus["bed_set"] = round(pinfo["heatedBeds"][0]["tempSet"])
    except urllib.error.URLError as e:
        print("multiprinter timeout error:", e)
        multiserver_interval = 10

    except socket.timeout as e:
        print("multiprinter timeout error:", e)
        multiserver_interval = 10

    except Exception as e:
        print("ERROR loading data from repetierserver", e)
        print(traceback.format_exc())


def nodes_reload():
    """
    This function (re)loads the nodes configuration from a json file
    """
    global shared
    nodesFile = "config/nodes.json"
    if os.path.isfile(nodesFile):
        f = open(nodesFile, "r")
        shared["node"] = json.loads(f.read())
        f.close()


def jobs_reload():
    """
    This function (re)loads the jobs list from json files
    """
    global shared
    projects = {}
    for project_dir in glob.glob(f"jobs/*"):
        projectName = project_dir.split("/")[-1]
        if not shared["activeProject"]:
            shared["activeProject"] = projectName
        projects[projectName] = projectName
    shared["project"] = projects

    jobs = {}
    for spool_dir in glob.glob(f"jobs/{shared['activeProject']}/*"):
        spool_name = spool_dir.split("/")[-1]
        jobId = f"{shared['activeProject']}/{spool_name}"
        jobfile = f"{spool_dir}/jobfile.json"
        if os.path.isfile(jobfile):
            f = open(jobfile, "r")
            jobdata = json.loads(f.read())
            f.close()
            jobs[jobId] = jobdata
        else:
            print("bad job:", jobId)
    shared["job"] = jobs


def autoprint_check(save=True):
    """
    This function checks for autoprint jobs
    """
    global shared
    # check autoprint
    changedJobs = {}
    for printer, printerConfig in shared["printerConfig"].items():
        printerStatus = shared["printerStatus"][printer]
        printerCommands = shared["printerCommands"][printer]
        if (
            printerStatus["status"] != "STANDBY"
            or printerCommands["next"]
            or printerStatus["active"]
            or not printerStatus["ready"]
        ):
            continue
        for jobId, jobData in shared["job"].items():
            if jobData["printer"] == printerConfig["name"] or jobData[
                "printer"
            ] in printerConfig.get("groups", []):
                if printerConfig.get("filament") == jobData.get("filament_type"):
                    if jobData.get("autoprint", 0) == 1 and int(
                        jobData["printed"]
                    ) < int(jobData["parts"]):
                        printerCommands["next"] = jobId
                        printerStatus["ready"] = 0
                        printerStatus["status"] = "JOB"
                        jobData["printed"] = int(jobData.get("printed", 0)) + 1
                        changedJobs[jobId] = True
                        if int(jobData["printed"]) == int(jobData["parts"]):
                            jobData["autoprint"] = 0
    if save:
        for jobId in changedJobs:
            open(f"jobs/{jobId}/jobfile.json", "w").write(
                json.dumps(shared["job"][jobId], indent=4)
            )


def printer_graph_history():
    """
    This function adds new values to the history graphs for each printer
    """
    global shared
    for printer, printerConfig in shared["printerConfig"].items():
        printerStatus = shared["printerStatus"][printer]
        for key in ["hotend", "bed", "hotend_set", "bed_set"]:
            hkey = f"{key}_history"
            if hkey not in printerStatus:
                printerStatus[hkey] = []
            hist = printerStatus[hkey]
            value = printerStatus.get(key, 0)
            hist.append(value)
            printerStatus[hkey] = hist[-20:]


def node_timeout_check():
    """
    This function checks the timeout of each node
    """
    global shared
    for nodeName, nodeData in shared["node"].items():
        last_seen = nodeData.get("last_seen", 0)
        if time.time() > last_seen + 20:
            nodeData["status"] = "OFFLINE"


def printer_timeout_check():
    """
    This function checks the timeout of each printer
    """
    global shared
    for printerId, printerStatus in shared["printerStatus"].items():
        last_seen = printerStatus.get("last_seen", 0)
        if time.time() > last_seen + 20:
            if printerStatus["running"] == "1":
                printerStatus["running"] = "0"
        elif printerStatus["running"] == "0":
            printerStatus["running"] = "1"


def printer_updates_send(printerId):
    """
    This function sends the printerstatus to each client/worker/node
    """
    global shared

    try:
        printerConfig = shared["printerConfig"][printerId]
        printerStatus = shared["printerStatus"][printerId]
        printerCommands = shared["printerCommands"][printerId]

        for clientId, clientData in shared["client"].copy().items():
            clientName = clientData.get("name")
            ctype = clientData.get("type")
            sid = clientData.get("sid")
            cprinter = clientData.get("printer")
            printerNode = printerConfig.get("node")

            if ctype == "webclient":
                socketio.emit(
                    "update",
                    {
                        "printer": printerId,
                        "status": printerStatus,
                        "config": printerConfig,
                    },
                    to=sid,
                )

            elif ctype == "worker":
                if printerNode == clientName and (
                    not cprinter or cprinter == printerId
                ):
                    socketio.emit(
                        "update",
                        {
                            "printer": printerId,
                            "status": printerStatus,
                            "config": printerConfig,
                            "commands": printerCommands,
                        },
                        to=sid,
                    )

            elif ctype == "supervisor":
                if printerNode == clientName:
                    socketio.emit(
                        "update",
                        {
                            "printer": printerId,
                            "status": printerStatus,
                            "config": printerConfig,
                            "commands": printerCommands,
                        },
                        to=sid,
                    )

        printerCommands["svcommand"] = ""
        printerCommands["next"] = ""
    except Exception as e:
        print("printer_updates_send error:", e)
        print(traceback.format_exc())


def background_thread():
    """
    This function is the background task
    * it can restart the master-node if not running
    * called the timeout-checks and updates

    """
    global shared

    history_last_update = 0
    printer_last_update = 0
    while True:
        socketio.sleep(1)
        try:
            # starting master node if not running
            try:
                procName = "qp-supervisor"
                found = False
                for proc in psutil.process_iter():
                    if proc.name() == procName:
                        found = True
                if not found:
                    print("try to start master node")
                    subprocess.run(
                        "nohup python3 node.py -u 'ws://127.0.0.1:5000' -n 'master' > '/tmp/log_node-master.log' 2>&1 &",
                        shell=True,
                    )
            except Exception:
                pass

            node_timeout_check()
            printer_timeout_check()
            autoprint_check()

            if time.time() >= history_last_update + history_interval:
                history_last_update = time.time()
                printer_graph_history()

            if time.time() >= printer_last_update + printer_interval:
                printer_last_update = time.time()
                for printerId in shared["printerConfig"]:
                    printer_updates_send(printerId)

        except Exception as e:
            print("loop error:", e)
            print(traceback.format_exc())


def multiprinter_thread():
    """
    This function is the background task for the multiprinter
    * get the printer-status from repetierserver

    """
    global shared
    global multiserver_interval

    multiserver_last_update = 0
    while True:
        socketio.sleep(1)
        try:
            if time.time() >= multiserver_last_update + multiserver_interval:
                multiserver_last_update = time.time()

                for printserverId, printserverData in shared[
                    "multiprintserver"
                ].items():
                    if (
                        printserverData.get("active") == "1"
                        and printserverData.get("type") == "repetierserver"
                    ):
                        url = printserverData["url"]
                        apiKey = printserverData["apiKey"]
                        if not apiKey:
                            apiKey = repetier.apikey_get(url)
                        sprinters = repetier.printer_list(url, apiKey)
                        if not sprinters:
                            continue
                        sortedPrinters = sorted(
                            sprinters, key=lambda item: item["name"]
                        )
                        for sprinterData in sortedPrinters:
                            sprinterId = sprinterData["slug"]
                            printerId = f"{apiKey}-{sprinterId}"
                            if printerId not in shared["printerStatus"]:
                                continue

                            printerStatus = shared["printerStatus"][printerId]
                            pinfo = repetier.printer_info(url, apiKey, sprinterId)
                            if pinfo:
                                jobInfo = repetier.printer_jobs(url, apiKey, sprinterId)
                                if jobInfo:
                                    printerStatus["running"] = sprinterData["online"]
                                    printerStatus["ready"] = sprinterData["online"]
                                    printerStatus["hotend"] = round(
                                        pinfo["extruder"][0]["tempRead"]
                                    )
                                    printerStatus["hotend_set"] = round(
                                        pinfo["extruder"][0]["tempSet"]
                                    )
                                    printerStatus["bed"] = round(
                                        pinfo["heatedBeds"][0]["tempRead"]
                                    )
                                    printerStatus["bed_set"] = round(
                                        pinfo["heatedBeds"][0]["tempSet"]
                                    )
                                    printerStatus["status"] = "PRINTING"
                                    printerStatus["active"] = {
                                        "jobId": jobInfo["job"],
                                        "traceId": jobInfo["job"],
                                        "status": "PRINTING",
                                    }
                                    printerStatus["percent"] = round(jobInfo["done"])
                                    printerStatus["remaining"] = round(
                                        (
                                            jobInfo["printTime"]
                                            - jobInfo["printedTimeComp"]
                                        )
                                        / 60
                                    )
                                else:
                                    printerStatus["status"] = "STANDBY"
                                    printerStatus["active"] = ""
                                    printerStatus["percent"] = ""
                            else:
                                printerStatus["status"] = "OFFLINE"
                                printerStatus["active"] = ""
                                printerStatus["percent"] = ""

                            printer_updates_send(printerId)

            multiserver_interval = 2
        except urllib.error.URLError as e:
            print("multiprinter loop timeout error:", e)
            multiserver_interval = 10

        except socket.timeout as e:
            print("multiprinter loop timeout error:", e)
            multiserver_interval = 10

        except Exception as e:
            print("multiprinter loop error:", e)
            print(traceback.format_exc())


# ##### Socket-Events #####


@socketio.event
def update(message):
    """
    This function gets all updates via websockets from the printer, clients and nodes
    """
    global shared

    # system update from nodes
    if "system" in message and request.sid in shared["client"]:
        client = shared["client"][request.sid]
        clientName = client["name"]
        update = False
        if clientName in shared["node"]:
            nodeData = shared["node"][clientName]
            nodeData["system"] = message["system"]
            nodeData["status"] = "ONLINE"
            nodeData["last_seen"] = time.time()
            update = True

    # devices update from nodes
    if "devices" in message and request.sid in shared["client"]:
        client = shared["client"][request.sid]
        clientName = client["name"]
        update = False
        if clientName in shared["node"]:
            nodeData = shared["node"][clientName]
            nodeData["devices"] = message["devices"]
            nodeData["status"] = "ONLINE"
            nodeData["last_seen"] = time.time()

            for device in nodeData["devices"]:
                if device.startswith("platform-") and ".usb-usb-0:1.1." in device:
                    rpiport = device.split(".")[3]
                    hubport = device.split(".")[4]
                    if ":" in hubport:
                        hubport = hubport.split(":")[0]
                    else:
                        hubport = ""
                    nodeData["devices"][device]["rpiport"] = rpiport
                    nodeData["devices"][device]["hubport"] = hubport

                for printerId, printerConfig in shared["printerConfig"].items():
                    if clientName == printerConfig.get("node") and nodeData["devices"][
                        device
                    ]["path"] == printerConfig.get("port"):
                        nodeData["devices"][device]["printer"] = printerConfig.get(
                            "name"
                        )

            update = True

    # printer update from worker-clients (and job-commands from frontend)
    if "printer" in message and message["printer"] in shared["printerConfig"]:
        if "setJob" in message:
            update = False
            printerId = message["printer"]
            printerConfig = shared["printerConfig"][printerId]
            printerStatus = shared["printerStatus"][printerId]
            printerCommands = shared["printerCommands"][printerId]
            jobId = message["setJob"]
            jobData = shared["job"][jobId]

            if (
                printerStatus["status"] == "STANDBY"
                and not printerCommands["next"]
                and not printerStatus["active"]
                and printerStatus["ready"]
            ):
                if printerConfig["type"] == "repetierserver":
                    repetier.printer_upload(
                        printerConfig["url"],
                        printerConfig["apiKey"],
                        printerConfig["nameOrigin"],
                        f"jobs/{jobId}/data.gcode",
                        jobId,
                    )

                else:
                    printerCommands["next"] = jobId
                    printerStatus["ready"] = 0
                    printerStatus["status"] = "JOB"

                jobData["printed"] = int(jobData["printed"]) + 1
                open(f"jobs/{jobId}/jobfile.json", "w").write(
                    json.dumps(jobData, indent=4)
                )
                update = True

        if "status" in message:
            update = False
            printerId = message["printer"]
            status = message["status"]
            printerStatus = shared["printerStatus"][printerId]
            for key, value in status.items():
                if printerStatus.get(key) != value:
                    if key == "active" and value:
                        job = value
                        jobId = job.get("jobId", "")
                        if jobId in shared["job"]:
                            jobData = shared["job"][jobId]
                            if "history" not in jobData:
                                jobData["history"] = {}
                            jobData["history"][time.time()] = {
                                "printer": printerId,
                                "status": job,
                            }
                            open(f"jobs/{jobId}/jobfile.json", "w").write(
                                json.dumps(jobData, indent=4)
                            )
                    printerStatus[key] = value
                    update = True

            printerStatus["last_seen"] = time.time()

            if update:
                printer_updates_send(printerId)

        if "config" in message:
            update = False
            printerId = message["printer"]
            config = message["config"]
            printerConfig = shared["printerConfig"][printerId]
            printerStatus = shared["printerStatus"][printerId]
            for key, value in config.items():
                if printerConfig.get(key) != value:
                    if key == "filament":
                        printerStatus["ready"] = 0
                    printerConfig[key] = value
                    update = True
            if update:
                printer_updates_send(printerId)
                printers_save()

        if "commands" in message:
            update = False
            printerId = message["printer"]
            commands = message["commands"]

            printerConfig = shared["printerConfig"][printerId]
            if printerConfig["type"] == "repetierserver":
                if commands.get("svcommand") == "KILL":
                    url = printerConfig["url"]
                    apiKey = printerConfig["apiKey"]
                    repetier.printer_stop(url, apiKey, printerConfig["nameOrigin"])

            else:
                printerCommands = shared["printerCommands"][printerId]
                for key, value in commands.items():
                    printerCommands[key] = value
                    update = True

            if update:
                printer_updates_send(printerId)


@socketio.event
def register(message):
    """
    This function is for the client registration
    """
    global shared

    clienttype = message.get("type")
    if clienttype == "webclient":
        clientname = request.sid
    elif clienttype == "supervisor":
        clientname = message["name"]
        if clientname and clientname not in shared["node"]:
            shared["node"][clientname] = {
                "status": "ONLINE",
                "devices": {},
            }
    else:
        clientname = message["name"]

    printerId = message.get("printer", "")
    shared["client"][request.sid] = {
        "type": clienttype,
        "name": clientname,
        "sid": request.sid,
        "printer": printerId,
    }


@socketio.event
def connect():
    """
    Unused callback function for the websockets
    """
    pass


@socketio.event
def disconnect():
    """
    callback function, called if a client are disconnected
    """
    global shared
    for clientSid, clientData in shared["client"].copy().items():
        if clientSid == request.sid:
            del shared["client"][clientSid]


# ##### HTML-Pages #####


@app.route("/")
def page_index():
    """
    This function generates the index-page
    """
    printers_reload()
    return render_template("index.html", data=shared, page="overview")


@app.route("/multiprintserver")
def page_multiprintserver():
    """
    This function generates the multiprintserver-page
    """
    return render_template(
        "multiprintserver.html", data=shared, page="multiprintserver"
    )


@app.route("/multiprintserver-setup")
def page_multiprintserversetup():
    """
    This function generates the multiprintserver setup-page
    """
    mpsId = request.args.get("multiprintserver")
    delete = request.args.get("delete")
    name = request.args.get("name")
    mpstype = request.args.get("type")
    mpsactive = request.args.get("active")
    url = request.args.get("url")
    apiKey = request.args.get("apiKey")

    if delete == "multiprintserver" and mpsId in shared["multiprintserver"]:
        del shared["multiprintserver"][mpsId]
        multiprintserver_save()
        printers_reload()
        return page_multiprintserver()

    if mpsId == "new":
        mpsId = str(uuid.uuid4())
        newdata = {
            "name": "repetier",
            "active": "1",
            "type": "repetierserver",
            "url": "http://ip:3311",
            "apiKey": "",
        }
        return render_template(
            "multiprintserver_setup.html",
            data=shared,
            setup=newdata,
            multiprintserver=mpsId,
            page="multiprintserver",
        )

    if name is not None:
        shared["multiprintserver"][mpsId] = {
            "name": name,
            "active": mpsactive,
            "type": mpstype,
            "url": url,
            "apiKey": apiKey,
        }
        multiprintserver_save()
        printers_reload()
        return page_multiprintserver()
    return render_template(
        "multiprintserver_setup.html",
        data=shared,
        setup=shared["multiprintserver"][mpsId],
        multiprintserver=mpsId,
        page="multiprintserver",
    )


@app.route("/printer")
def page_printer():
    """
    This function generates the printer-page
    """
    printers_reload()
    return render_template("printer.html", data=shared, page="printer")


@app.route("/printerlist")
def printerlist():
    """
    This function generates a list of printers as html-table
    """
    filtered = {}
    jobId = request.args.get("job")
    jobData = shared["job"].get(jobId)
    sortedDict = sorted(
        shared["printerConfig"].items(), key=lambda item: item[1]["name"]
    )
    for printerId, printerConfig in sortedDict:
        printerStatus = shared["printerStatus"].get(printerId, {})
        if (
            printerStatus["status"] == "STANDBY"
            and int(printerStatus["running"]) == 1
            and int(printerStatus["ready"]) == 1
            and printerConfig["filament"] == jobData.get("filament_type")
        ):
            filtered[printerId] = printerConfig

    data = {
        "job": jobId,
        "printers": filtered,
        "printerStatus": shared["printerStatus"],
    }
    return render_template("printerlist.html", data=data)


@app.route("/node-setup")
def page_node_setup():
    """
    This function generates the node setup-page
    """
    node = request.args.get("node")
    delete = request.args.get("delete")

    if not node:
        return page_nodes()

    if delete == "node" and node != "master":
        if node in shared["node"]:
            del shared["node"][node]
            print("saveing nodes.json")
            open("config/nodes.json", "w").write(json.dumps(shared["node"], indent=4))

    return page_nodes()


@app.route("/job-setup", methods=["GET", "POST"])
def page_job_setup():
    """
    This function generates the job setup-page
    """
    job = request.args.get("job")
    delete = request.args.get("delete")

    if delete == "job" and job:
        if os.path.isdir(f"jobs/{job}"):
            rmtree(f"jobs/{job}")
            jobs_reload()
            return page_jobs()

    # generate list of printers and groups
    pgList = []
    for printerId, printerConfig in shared["printerConfig"].items():
        if printerConfig["name"] not in pgList:
            pgList.append(printerConfig["name"])
        for group in printerConfig["groups"]:
            if group not in pgList:
                pgList.append(group)

    if job == "new":
        return render_template(
            "job_upload.html",
            data=shared,
            page="jobs",
            pglist=pgList,
            filamentlist=filamentList,
        )

    save = False
    if job in shared["job"]:
        for key, value in request.args.items():
            if key not in ["job", "delete"]:
                shared["job"][job][key] = value
                save = True
    else:
        return page_jobs()

    if save:
        open(f"jobs/{job}/jobfile.json", "w").write(
            json.dumps(shared["job"][job], indent=4)
        )
        return page_jobs()

    return render_template(
        "job_setup.html",
        data=shared,
        job=job,
        page="jobs",
        pglist=pgList,
        filamentlist=filamentList,
    )


@app.route("/printer-setup")
def page_printer_setup():
    """
    This function generates the printer setup-page
    """
    printerId = request.args.get("printer")
    delete = request.args.get("delete")

    if not printerId:
        return page_printer()

    if delete == "printer":
        if printerId in shared["printerConfig"]:
            del shared["printerConfig"][printerId]
            del shared["printerStatus"][printerId]
            del shared["printerCommands"][printerId]
            printers_save()
        return page_printer()

    if printerId == "new":
        # create new printer
        printerId = str(uuid.uuid4())
        shared["printerConfig"][printerId] = copy.deepcopy(emptyPrinterConfig)
        shared["printerStatus"][printerId] = copy.deepcopy(emptyPrinterStatus)
        shared["printerCommands"][printerId] = copy.deepcopy(emptyPrinterCommands)
        printerConfig = shared["printerConfig"][printerId]
        printerConfig["name"] = f"Printer-{printerId[:6]}"
        if shared["node"]:
            printerConfig["node"] = list(shared["node"].keys())[0]

    if printerId not in shared["printerConfig"]:
        return page_printer()

    printerConfig = shared["printerConfig"][printerId]

    save = False
    for key, value in request.args.items():
        if key not in ["printer", "delete"]:
            if key in ["filament_types", "groups"]:
                printerConfig[key] = value.split(",")
            else:
                printerConfig[key] = value
            save = True

    pnode = printerConfig["node"]
    if pnode and pnode not in shared["node"]:
        shared["node"][pnode] = {
            "status": "ONLINE",
            "devices": {},
        }

    if save:
        printers_save()
        return page_printer()

    images = []
    for imagepath in glob.glob("images/*"):
        images.append(imagepath.split("/")[-1])

    return render_template(
        "printer_setup.html",
        data=shared,
        printer=printerId,
        images=images,
        page="printer",
    )


@app.route("/nodes")
def page_nodes():
    """
    This function generates the nodes-page
    """
    return render_template("nodes.html", data=shared, page="nodes")


@app.route("/jobs")
def page_jobs():
    """
    This function generates the jobs-page
    """
    project = request.args.get("project", "")
    filterPrinted = request.args.get("printed", "0")
    filtered = {}

    if project and project in shared["project"]:
        shared["activeProject"] = project
        jobs_reload()

    sortedDict = sorted(shared["job"].items(), key=lambda item: item[1]["date"])
    sortedDict.reverse()

    for jobId, jobData in sortedDict:

        if filterPrinted == "0" and (
            int(jobData["printed"]) != 0
            and int(jobData["printed"]) >= int(jobData["parts"])
        ):
            continue

        filtered[jobId] = jobData
        filtered[jobId]["date_str"] = datetime.datetime.fromtimestamp(
            int(filtered[jobId]["date"])
        ).strftime("%d.%m.%Y, %H:%M:%S")

    return render_template("jobs.html", data=shared, jobs=filtered, page="jobs")


@app.route("/joblist")
def joblist():
    """
    This function generates a list of printers as html-table
    """
    printerId = request.args.get("printer")
    filterPrinted = request.args.get("printed", "0")

    filtered = {}
    printerConfig = shared["printerConfig"].get(printerId, {})
    sortedDict = sorted(shared["job"].items(), key=lambda item: item[1]["date"])
    sortedDict.reverse()
    for jobId, jobData in sortedDict:
        if filterPrinted == "0" and (
            int(jobData["printed"]) != 0
            and int(jobData["printed"]) >= int(jobData["parts"])
        ):
            continue
        if (
            not printerId
            or jobData["printer"]
            or jobData["printer"] == printerConfig.get("name")
            or jobData["printer"] in printerConfig.get("groups", [])
        ):
            if not jobData.get("filament_type") or printerConfig.get(
                "filament"
            ) == jobData.get("filament_type"):
                filtered[jobId] = jobData
                filtered[jobId]["date_str"] = datetime.datetime.fromtimestamp(
                    int(filtered[jobId]["date"])
                ).strftime("%d.%m.%Y, %H:%M:%S")

    data = {
        "printer": printerId,
        "jobs": filtered,
    }
    return render_template("joblist.html", data=data)


@app.route("/jobdata")
def jobdata():
    """
    This function returns a specific job as json
    """
    job = request.args.get("job")
    jobData = {}
    if job and job in shared["job"]:
        jobData = shared["job"][job]

    return json.dumps(jobData, indent=4)


@app.route("/printerconfig")
def printerconfig():
    """
    This function returns a specific printer-config as json
    """
    printerId = request.args.get("printer")
    if printerId not in shared["printerConfig"]:
        return "{}"
    return json.dumps(shared["printerConfig"][printerId], indent=4)


@app.route("/clients")
def page_clients():
    """
    This function generates the clients-page
    """
    return render_template("clients.html", data=shared, page="clients")


@app.route("/gcode")
def gcode():
    """
    This function returns the gcod-file of a specific job
    """
    job = request.args.get("job")
    gcode = open(f"jobs/{job}/data.gcode", "rb").read().decode()
    return Response(gcode, mimetype="text/plain")


@app.route("/gcodefile")
def gcodefile():
    """
    This function returns the gcod-file of a specific job
    """
    job = request.args.get("job")
    jobData = shared["job"][job]
    filename = jobData["filename"]
    return send_file(
        f"jobs/{job}/data.gcode",
        mimetype="text/plain",
        download_name=filename,
        as_attachment=True,
    )


@app.route("/image")
def image():
    """
    This function returns an image
    """
    job = request.args.get("job")
    image = request.args.get("image")
    filename = ""

    if job and job in shared["job"]:
        jobData = shared["job"][job]
        thumbs = jobData.get("thumbs", [])
        if thumbs:
            filename = f"jobs/{job}/thumb_{thumbs[-1]}.jpg"
    elif image:
        if image:
            filename = f"images/{image}"

    if filename and os.path.isfile(filename):
        image = open(filename, "rb").read()
        return image

    return ""


@app.route("/3dview")
def page_3dview():
    """
    This function generates a 3D-View-page for an specific job
    """
    job = request.args.get("job")
    return render_template("3dview.html", job=job, page="jobs")


@app.route("/api/version")
def api_version():
    """
    This function simulates the Octoprint-API (version)
    """
    return '{"api":"0.1","server":"1.5.3","text":"OctoPrint 1.5.3"}'


@app.route("/api/files/local", methods=["GET", "POST"])
def api_files_local():
    """
    This function simulates the Octoprint-API (file-upload)
    """
    global shared

    client = request.form.get("client") or ""

    if request.method == "POST":
        timestamp = time.time()
        do_print = request.form.get("print", False)
        parts = int(request.form.get("parts") or 1)
        filename = request.form.get("filename") or ""
        filament_type = request.form.get("filament_type") or ""
        printer = request.form.get("printer") or ""
        project = request.form.get("project")
        f = request.files["file"]

        if not project:
            project = shared["activeProject"]

        if not os.path.isdir(f"jobs/{project}"):
            os.makedirs(f"jobs/{project}")

        jobId = f"{project}/{str(uuid.uuid4())}"
        jobDir = f"jobs/{jobId}"
        gfile = f"{jobDir}/data.gcode"
        jobfile = f"{jobDir}/jobfile.json"

        # safe metadata
        os.makedirs(jobDir)
        f.save(gfile)
        size = os.stat(gfile).st_size

        try:
            analyze = gcode_analyze(jobId)
            thumbs = gcode_thumbs(jobId)
            info = gcode_info(jobId)

            autoprint = 0
            if do_print:
                autoprint = 1

            if not filename:
                filename = f.filename

            jobdata = {
                "date": timestamp,
                "filename": filename,
                "size": size,
                "thumbs": thumbs,
                "history": {},
                "printer": "",
                "printed": 0,
                "parts": int(parts),
                "autoprint": 0,
            }
            for key, value in info.items():
                jobdata[key] = value
            for key, value in analyze.items():
                jobdata[key] = value

            # check filament type
            for ftype in filamentList:
                if f"_{ftype}_" in jobdata["filename"]:
                    jobdata["filament_type"] = ftype
                    break

            mapping = {
                "printer": printer or jobdata["printer"],
                "filament_type": filament_type or jobdata.get("filament_type", ""),
                "filament_mm": str(
                    jobdata.get("filament", {}).get("tool0", {}).get("length", 0)
                ),
                "filament_cm3": str(
                    jobdata.get("filament", {}).get("tool0", {}).get("volume", 0)
                ),
                "filament_g": "0",
                "filament_cost": "0",
                "total_g": "0",
                "total_cost": "0",
                "duration": str(jobdata.get("estimatedPrintTime", "0")),
            }
            for key, value in mapping.items():
                if key not in jobdata:
                    jobdata[key] = value

            f = open(jobfile, "w")
            f.write(json.dumps(jobdata, indent=4))
            f.close()

        except Exception as e:
            print("ERROR: creating new job", e)
            print(traceback.format_exc())
            rmtree(jobDir)

    jobs_reload()

    if client == "html":
        return page_jobs()

    return json.dumps({"status": "ok"}, indent=4)


@app.route("/favicon.ico")
def favicon():
    """
    This function returns the favicon.ico
    """
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


if __name__ == "__main__":
    nodes_reload()
    printers_reload()
    jobs_reload()

    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)

    with thread_lock:
        if mpthread is None:
            mpthread = socketio.start_background_task(multiprinter_thread)

    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    print("starting server at: http://0.0.0.0:5000")
    socketio.run(app, debug=False, host="0.0.0.0", port=5000)
