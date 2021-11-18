import json
import requests
import urllib.request

timeout = 1


def apikey_get(url):
    with urllib.request.urlopen(f"{url}/printer/info", timeout=timeout) as response:
        rawData = response.read()
        if rawData:
            data = json.loads(rawData)
            return data["apikey"]
    return ""


def printer_list(url, apiKey):
    with urllib.request.urlopen(
        f"{url}/printer/info?apikey={apiKey}", timeout=timeout
    ) as response:
        rawData = response.read()
        if rawData:
            data = json.loads(rawData)
            return data["printers"]
    return []


def printer_info(url, apiKey, printerSlug):
    with urllib.request.urlopen(
        f"{url}/printer/api/{printerSlug}?a=stateList&apikey={apiKey}&data=includeHistory=false",
        timeout=timeout,
    ) as response:
        rawData = response.read()
        if rawData:
            data = json.loads(rawData)
            if printerSlug in data:
                return data[printerSlug]
            return {}


def printer_stop(url, apiKey, printerSlug):
    with urllib.request.urlopen(
        f"{url}/printer/api/{printerSlug}?a=stopJob&apikey={apiKey}",
        timeout=timeout,
    ) as response:
        print(response.read())


def printer_jobs(url, apiKey, printerSlug):
    with urllib.request.urlopen(
        f"{url}/printer/api/{printerSlug}?a=listPrinter&apikey={apiKey}",
        timeout=timeout,
    ) as response:
        rawData = response.read()
        if rawData:
            data = json.loads(rawData)
            jobInfo = {}
            for job in data:
                if (
                    job.get("slug") == printerSlug
                    and job.get("active")
                    and job.get("job") != "none"
                ):
                    jobInfo = job
            return jobInfo
    return {}


def printer_upload(url, apiKey, printerSlug, filepath, targetname=None):
    if not targetname:
        targetname = filepath.split("/")[-1]
    posturl = f"{url}/printer/job/{printerSlug}?name={targetname}&autostart=true"
    filehandler = open(filepath, "rb")
    multipart_form_data = {
        "filename": (targetname, filehandler),
        "a": (None, "upload"),
    }
    headers = {"x-api-key": apiKey}
    response = requests.post(posturl, files=multipart_form_data, headers=headers)
    print(response.content)
