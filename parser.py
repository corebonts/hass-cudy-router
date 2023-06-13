"""Helper methods to parse HTML returned by Cudy routers"""

import re
from typing import Any
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE

from .const import SECTION_DETAILED


def add_unique(data: dict[str, Any], key: str, value: Any):
    """Adds a new entry with unique ID"""

    i = 1
    unique_key = key
    while data.get(unique_key):
        i += 1
        unique_key = f"{key}{i}"
    data[unique_key] = value


def parse_tables(input_html: str) -> dict[str, Any]:
    """Parses an HTML table extracting key-value pairs"""

    data: dict[str, str] = {}
    soup = BeautifulSoup(input_html, "html.parser")
    tables = soup.find_all("table")
    for table in tables:
        for row in table.find_all("tr"):
            cols = row.css.select("td p.visible-xs")
            row_data: list[str] = []
            for col in cols:
                stripped_text = col.text.strip()
                if stripped_text:
                    row_data.append(stripped_text)
            if len(row_data) > 1:
                add_unique(data, row_data[0], re.sub("[\n]", "", row_data[1]))
            elif len(row_data) == 1:
                add_unique(data, row_data[0], "")

    return data


def parse_speed(input_string: str) -> float:
    """Parses transfer speed as megabits per second"""

    if not input_string:
        return None
    if input_string.lower().endswith(" kbps"):
        return round(float(input_string.split(" ")[0]) / 1024, 2)
    if input_string.lower().endswith(" mbps"):
        return float(input_string.split(" ")[0])
    if input_string.lower().endswith(" gbps"):
        return float(input_string.split(" ")[0]) * 1024
    if input_string.lower().endswith(" bps"):
        return round(float(input_string.split(" ")[0]) / 1024 / 1024, 2)
    return 0


def get_all_devices(input_html: str) -> dict[str, Any]:
    """Parses an HTML table extracting key-value pairs"""
    devices = []
    soup = BeautifulSoup(input_html, "html.parser")
    for br_element in soup.find_all("br"):
        br_element.replace_with("\n" + br_element.text)
    tables = soup.find_all("table")
    for table in tables:
        for row in table.find_all("tr"):
            ip, mac, up_speed, down_speed, hostname = [None, None, None, None, None]
            cols = row.css.select("td div")
            for col in cols:
                div_id = col.attrs.get("id")
                content_element = col.css.select_one("p.visible-xs")
                if not div_id or not content_element:
                    continue
                content = content_element.text.strip()
                if "\n" in content:
                    if div_id.endswith("ipmac"):
                        ip, mac = [x.strip() for x in content.split("\n")]
                    if div_id.endswith("speed"):
                        up_speed, down_speed = [x.strip() for x in content.split("\n")]
                    if div_id.endswith("hostname"):
                        hostname = content.split("\n")[0].strip()
            if mac or ip:
                devices.append(
                    {
                        "hostname": hostname,
                        "ip": ip,
                        "mac": mac,
                        "up_speed": parse_speed(up_speed),
                        "down_speed": parse_speed(down_speed),
                    }
                )

    return devices


def get_sim_value(input_html: str) -> str:
    """Gets the SIM slot value out of the displayed icon"""

    soup = BeautifulSoup(input_html, "html.parser")
    sim_icon = soup.css.select_one("i.icon[class*='sim']")
    if sim_icon:
        classnames = sim_icon.attrs["class"]
        classname = next(
            iter([match for match in classnames if "sim" in match]),
            "",
        )
        if "sim1" in classname:
            return "Sim 1"
        if "sim2" in classname:
            return "Sim 2"
    return STATE_UNAVAILABLE


def get_signal_strength(rssi: int) -> int:
    """Gets the signal strength from the RSSI value"""

    if rssi:
        if rssi > 20:
            return 4
        if rssi > 15:
            return 3
        if rssi > 10:
            return 2
        if rssi > 5:
            return 1
        return 0
    return STATE_UNAVAILABLE


def as_int(string: str | None):
    """Parses string as integer or returns None"""

    if not string:
        return None
    return int(string)

def hex_as_int(string: str | None):
    """Parses hexadecimal string as integer or returns None"""

    if not string:
        return None
    return int(string, 16)


def get_band(raw_band_info: str):
    """Gets band information"""

    if raw_band_info:
        match = re.compile(
            r".*BAND\s*(?P<band>\d+)\s*/\s*(?P<bandwidth>\d+)\s*MHz.*"
        ).match(raw_band_info)
        if match:
            return f"B{match.group('band')}"

    return None


def get_seconds_duration(raw_duration: str) -> int:
    """Parses string duration and returns it as seconds"""

    if not raw_duration:
        return None
    duration_parts = raw_duration.lower().split()
    duration = relativedelta()

    for i, part in enumerate(duration_parts):
        if part.count(":") == 2:
            hours, minutes, seconds = part.split(":")
            duration += relativedelta(
                hours=as_int(hours), minutes=as_int(minutes), seconds=as_int(seconds)
            )
        elif i == 0:
            continue
        elif part.startswith("year"):
            duration += relativedelta(years=as_int(duration_parts[i - 1]))
        elif part.startswith("month"):
            duration += relativedelta(months=as_int(duration_parts[i - 1]))
        elif part.startswith("week"):
            duration += relativedelta(weeks=as_int(duration_parts[i - 1]))
        elif part.startswith("day"):
            duration += relativedelta(days=as_int(duration_parts[i - 1]))

    # Get absolute duration from relative duration (considering different month lengths)
    return (datetime.now() - (datetime.now() - duration)).total_seconds()


def parse_devices(input_html: str, device_list_str: str) -> dict[str, Any]:
    """Parses devices page"""

    devices = get_all_devices(input_html)
    data = {"device_count": {"value": len(devices)}}
    if devices:
        top_download_device = max(devices, key=lambda item: item.get("down_speed"))
        data["top_downloader_speed"] = {"value": top_download_device.get("down_speed")}
        data["top_downloader_mac"] = {"value": top_download_device.get("mac")}
        data["top_downloader_hostname"] = {"value": top_download_device.get("hostname")}
        top_upload_device = max(devices, key=lambda item: item.get("up_speed"))
        data["top_uploader_speed"] = {"value": top_upload_device.get("up_speed")}
        data["top_uploader_mac"] = {"value": top_upload_device.get("mac")}
        data["top_uploader_hostname"] = {"value": top_upload_device.get("hostname")}

        data[SECTION_DETAILED] = {}
        device_list = [x.strip() for x in (device_list_str or "").split(",")]
        for device in devices:
            if device.get("mac") in device_list:
                data[SECTION_DETAILED][device.get("mac")] = device
            if device.get("hostname") in device_list:
                data[SECTION_DETAILED][device.get("hostname")] = device

        data["total_down_speed"] = {
            "value": sum(device.get("down_speed") for device in devices) or 0.0
        }
        data["total_up_speed"] = {
            "value": sum(device.get("up_speed") for device in devices) or 0.0
        }
    return data


def parse_modem_info(input_html: str) -> dict[str, Any]:
    """Parses modem info page"""

    raw_data = parse_tables(input_html)
    cellid = hex_as_int(raw_data.get("Cell ID"))
    pcc = raw_data.get("PCC") or (
        f"BAND {raw_data.get('Band')} / {raw_data.get('DL Bandwidth')}"
        if (raw_data.get("Band") and raw_data.get("DL Bandwidth"))
        else None
    )
    scc1 = raw_data.get("SCC")
    scc2 = raw_data.get("SCC2")
    scc3 = raw_data.get("SCC3")
    scc4 = raw_data.get("SCC4")
    data: dict[str, dict[str, Any]] = {
        "network": {
            "value": (raw_data.get("Network Type") or "").replace(" ...", ""),
            "attributes": {"mcc": raw_data.get("MCC"), "mnc": raw_data.get("MNC")},
        },
        "connected_time": {
            "value": get_seconds_duration(raw_data.get("Connected Time"))
        },
        "signal": {"value": get_signal_strength(as_int(raw_data.get("RSSI")))},
        "rssi": {"value": as_int(raw_data.get("RSSI"))},
        "rsrp": {"value": as_int(raw_data.get("RSRP"))},
        "rsrq": {"value": as_int(raw_data.get("RSRQ"))},
        "sinr": {"value": as_int(raw_data.get("SINR"))},
        "sim": {"value": get_sim_value(input_html)},
        "band": {
            "value": "+".join(
                filter(
                    None,
                    (get_band(pcc), get_band(scc1), get_band(scc2), get_band(scc3)),
                )
                or None
            ),
            "attributes": {
                "pcc": get_band(pcc),
                "scc1": get_band(scc1),
                "scc2": get_band(scc2),
                "scc3": get_band(scc3),
                "scc4": get_band(scc4),
            },
        },
        "cell": {
            "value": raw_data.get("Cell ID"),
            "attributes": {
                "id": cellid,
                "enb": cellid // 256 if cellid else None,
                "sector": cellid % 256 if cellid else None,
                "pcid": as_int(raw_data.get("PCID")),
            },
        },
    }
    return data
