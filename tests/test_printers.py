import os
import pytest

from server import shared, printers_reload, printers_save, jobs_reload, autoprint_check

os.chdir("tests")


@pytest.mark.parametrize(
    (
        "printerStatus, printerConfig, printerCommands, printed, autoprint, printed2, autoprint2"
    ),
    (
        (
            {"running": 1, "status": "STANDBY", "ready": 1},
            {"filament": "PETG"},
            {"next": ""},
            1,
            1,
            2,
            0,
        ),
        (
            {"running": 1, "status": "STANDBY", "ready": 1},
            {"filament": "PLA"},
            {"next": ""},
            0,
            1,
            0,
            1,
        ),
        (
            {"running": 1, "status": "INIT", "ready": 1},
            {"filament": "PETG"},
            {"next": ""},
            0,
            1,
            0,
            1,
        ),
        (
            {"running": 1, "status": "STANDBY", "ready": 0},
            {"filament": "PETG"},
            {"next": ""},
            0,
            1,
            0,
            1,
        ),
        (
            {"running": 0, "status": "STANDBY", "ready": 1},
            {"filament": "PETG"},
            {"next": ""},
            1,
            1,
            2,
            0,
        ),
    ),
)
def test_autoprint(
    printerStatus,
    printerConfig,
    printerCommands,
    printed,
    autoprint,
    printed2,
    autoprint2,
):

    expected = {
        "1234": {
            "name": "v1",
            "filament": "PLA",
            "filament_types": ["PLA", "PETG", "ABS", "TPU", "NYLON"],
            "groups": ["marlin-20x20"],
            "image": "generig.jpg",
            "node": "master",
            "type": "simulator",
            "port": "",
            "baud": "115200",
        }
    }

    shared["printerConfig"] = expected
    printers_save(backup=False)

    shared["printerConfig"] = {}
    printers_reload()

    assert shared["printerConfig"] == expected

    jobs_reload()

    assert shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["printed"] == 0
    assert shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["parts"] == 2
    assert shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["autoprint"] == 1

    shared["printerStatus"]["1234"]["running"] = printerStatus["running"]
    shared["printerStatus"]["1234"]["status"] = printerStatus["status"]
    shared["printerStatus"]["1234"]["ready"] = printerStatus["ready"]
    shared["printerConfig"]["1234"]["filament"] = printerConfig["filament"]
    shared["printerCommands"]["1234"]["next"] = printerCommands["next"]
    autoprint_check(save=False)
    assert shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["printed"] == printed
    assert (
        shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["autoprint"] == autoprint
    )

    shared["printerStatus"]["1234"]["running"] = printerStatus["running"]
    shared["printerStatus"]["1234"]["status"] = printerStatus["status"]
    shared["printerStatus"]["1234"]["ready"] = printerStatus["ready"]
    shared["printerConfig"]["1234"]["filament"] = printerConfig["filament"]
    shared["printerCommands"]["1234"]["next"] = printerCommands["next"]
    autoprint_check(save=False)
    assert shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["printed"] == printed2
    assert (
        shared["job"]["91e1cfcc-c393-43df-b905-ab4ce2d1c6ed"]["autoprint"] == autoprint2
    )
