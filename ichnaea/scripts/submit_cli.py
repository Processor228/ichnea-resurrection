import sys
import subprocess
import tqdm
import threading
import time
import json
import urllib.request
import urllib.parse



class AccessPoint:
    def __init__(
        self,
        ssid: str | None,
        bssid: str,
        signal: int,
        channel: int,
        frequency_mhz: int,
        in_use: bool = False,
    ):
        self.ssid = ssid
        self.bssid = bssid
        self.signal = signal
        self.channel = channel
        self.frequency_mhz = frequency_mhz
        self.in_use = in_use

    @classmethod
    def from_dict(cls, data: dict) -> "AccessPoint":
        return cls(
            ssid=data.get("ssid"),
            bssid=data["bssid"],
            signal=int(data["signal"]),
            channel=int(data["channel"]),
            frequency_mhz=int(data["frequency_mhz"]),
            in_use=data.get("in_use", False),
        )

    def __str__(self) -> str:
        ssid = self.ssid or "<hidden>"
        active = "*" if self.in_use else " "
        return (
            f"{active} {ssid:20} "
            f"{self.bssid} "
            f"{self.signal:3d}% "
            f"ch {self.channel:2d} "
            f"{self.frequency_mhz} MHz"
        )

    def __repr__(self) -> str:
        return (
            "AccessPoint("
            f"ssid={self.ssid!r}, "
            f"bssid={self.bssid!r}, "
            f"signal={self.signal}, "
            f"channel={self.channel}, "
            f"frequency_mhz={self.frequency_mhz}, "
            f"in_use={self.in_use}"
            ")"
        )


def scan_wifi() -> list[AccessPoint]:
    cmd = [
        "nmcli",
        "-f",
        "IN-USE,SSID,BSSID,SIGNAL,CHAN,FREQ",
        "dev",
        "wifi",
        "list",
    ]

    result_holder = {}

    def run_nmcli():
        result_holder["result"] = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

    thread = threading.Thread(target=run_nmcli)
    thread.start()

    # tqdm spinner while nmcli runs
    with tqdm.tqdm(
        desc="Scanning Wi-Fi networks",
        bar_format="{desc} {elapsed}",
    ) as bar:
        while thread.is_alive():
            time.sleep(0.1)
            bar.refresh()

    thread.join()
    result = result_holder["result"]
    print(result)
    access_points: list[AccessPoint] = []

    lines = result.stdout.strip().split("\n")

    # skip header
    for line in lines[1:]:
        print(line)
        fields = line.split()
        if not fields:
            continue

        if fields[0] == "*":
            data = {
                "in_use": True,
                "ssid": fields[1] or None,
                "bssid": fields[2],
                "signal": fields[3],
                "channel": fields[4],
                "frequency_mhz": fields[5],
            }
        else:
            data = {
                "in_use": False,
                "ssid": fields[0] or None,
                "bssid": fields[1],
                "signal": fields[2],
                "channel": fields[3],
                "frequency_mhz": fields[4],
            }

        try:
            ap = AccessPoint.from_dict(data)
            access_points.append(ap)
        except:
            print("Couldn't parse a wifi network: ", data["ssid"])

    return access_points


def submit(wifis: list[AccessPoint], position: tuple[float, float]):
    url = "http://127.0.0.1:8000/v2/geosubmit"

    # Build payload
    payload = {
        "items": [
            {
                "wifiAccessPoints": [
                    {"macAddress": ap.bssid}
                    for ap in wifis
                    if ap.bssid
                ],
                "position": {
                    "latitude": position[0],
                    "longitude": position[1],
                },
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")

    params = urllib.parse.urlencode({"key": "test"})
    full_url = f"{url}?{params}"

    request = urllib.request.Request(
        full_url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=5) as response:
        response_body = response.read().decode("utf-8")

    return response_body


def main(argv):
    aps = scan_wifi()

    print("Discovered networks:")
    for ap in aps:
        print(ap)

    lat, lon = 55.747640, 48.742494
    try:
        lat, lon = [float(x) for x in input("What is your current location?\n Please, enter lat, lon (if you are sitting on your ass at the house, \nits 55.747640 48.742494): ").split()]
    except:
        # default coords
        pass

    print(lat, lon)

    if input("Submit your data? y/n ").lower() == "y":
        submit(aps, (lat, lon))

    return 0


# 55.747640 48.742494
if __name__ == "__main__":
    sys.exit(main(sys.argv))
