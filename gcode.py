import base64
import subprocess
import json
import platform


def gcode_thumbs(myuuid):
    spool_dir = f"jobs/{myuuid}"
    gfile = f"{spool_dir}/data.gcode"
    f = open(gfile, "r")
    gdata = f.read()
    f.close()
    start = ""
    thumbnails = {}
    for line in gdata.split("\n"):
        if line.startswith("; thumbnail end"):
            imagedata = base64.b64decode(thumbnails[start])
            imagefile = f"{spool_dir}/thumb_{start}.jpg"
            f = open(imagefile, "wb")
            f.write(imagedata)
            f.close()
            start = ""
        elif line.startswith("; thumbnail begin "):
            start = line.split()[3]
            thumbnails[start] = ""
        elif start:
            thumbnails[start] += line.split()[1]

    if not thumbnails:
        imagefilePng = f"{spool_dir}/thumb_normal.png"
        imagefile = f"{spool_dir}/thumb_normal.jpg"
        c2pCmd = f"bin/gcode2png --output={imagefilePng} {gfile} && convert {imagefilePng} {imagefile}"
        print("Execute:", c2pCmd)
        subprocess.run(c2pCmd, shell=True)
        thumbnails["normal"] = "thumb_normal.png"

    return list(thumbnails.keys())


def gcode_info(myuuid):
    spool_dir = f"jobs/{myuuid}"
    gfile = f"{spool_dir}/data.gcode"
    f = open(gfile, "r")
    gdata = f.read()
    f.close()
    info = {}
    mapping = {
        "printer": "physical_printer_settings_id",
        "filament_mm": "filament used [mm]",
        "filament_cm3": "filament used [cm3]",
        "filament_g": "filament used [g]",
        "filament_cost": "filament cost",
        "total_g": "total filament used [g]",
        "total_cost": "total filament cost",
        "duration": "estimated printing time (normal mode)",
    }
    for line in gdata.split("\n"):
        for key, value in mapping.items():
            if line.startswith(f"; {value} = "):
                info[key] = line.split("=")[1].strip()
    return info


def gcode_analyze(myuuid):
    # https://github.com/eyal0/OctoPrint-PrintTimeGenius/tree/master/octoprint_PrintTimeGenius/analyzers
    machine = platform.machine()
    marlin_calc = f"./bin/marlin-calc.{machine}"
    spool_dir = f"jobs/{myuuid}"
    gfile = f"{spool_dir}/data.gcode"
    analyze = {}
    result = subprocess.run([marlin_calc, gfile], stdout=subprocess.PIPE)
    for line in result.stdout.split(b"\n"):
        if line.startswith(b"Analysis: "):
            analyze = json.loads(line[10:])
    return analyze
