import argparse
import platform
import re
import requests
import subprocess


parser = argparse.ArgumentParser(description='Locate me by doing a wifi scan.')
parser.add_argument(
    "-v", "--verbose",
    action="store_true",
    help="Enable verbose logging.  Helpful when debugging."
)
args = parser.parse_args()


# Flag for detailed debugging output
_VERBOSE_ = args.verbose


def scan_wifi():
    system = platform.system()
    networks = []

    if system == 'Windows':
        # Run Windows scan command
        result = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
                               capture_output=True, text=True)
        output = result.stdout

        # Parse networks and BSSIDs
        ssid = None
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('SSID'):
                # Extract SSID name
                ssid = line.split(':', 1)[1].strip()
            elif ssid and 'BSSID' in line:
                # Extract BSSID and signal percentage
                bssid = line.split(':', 1)[1].strip()
            elif ssid and 'Signal' in line:
                signal_str = line.split(':', 1)[1].replace('%', '').strip()
                if signal_str.isdigit():
                    signal_percent = int(signal_str)
                    # Convert percentage to dBm approximation
                    signal_dbm = (signal_percent / 2) - 100
                    networks.append({
                        'ssid': ssid,
                        'bssid': bssid,
                        'signal_dbm': round(signal_dbm, 1)
                    })

    elif system == 'Linux':
        # Run Linux scan command
        result = subprocess.run(['nmcli', '-t', '-f', 'BSSID,SSID,SIGNAL', 'dev', 'wifi', 'list', '--rescan', 'yes'],
                               capture_output=True, text=True)
        output = result.stdout

        # Parse each network entry
        for line in output.split('\n'):
            line = line.replace(r"\:","|")
            if ':' not in line:
                continue
            parts = line.split(':')
            parts[0] = parts[0].replace("|", ":")
            if len(parts) >= 3:
                bssid = parts[0].strip()
                ssid = parts[1].strip()
                signal_str = parts[2].replace('%', '').strip()
                if signal_str.isdigit():
                    signal_percent = int(signal_str)
                    # Convert percentage to dBm approximation
                    signal_dbm = (signal_percent / 2) - 100
                    networks.append({
                        'ssid': ssid,
                        'bssid': bssid,
                        'signal_dbm': round(signal_dbm, 1)
                    })
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

    return networks

# API description:
# https://ichnaea.readthedocs.io/en/latest/api/geolocate.html
# https://beacondb.net/
def locate_with_beacondb(networks, user_agent="BeaconDB-Python-Locator/1.0", verbose=False):
    """
    Get location from BeaconDB using WiFi MAC addresses
    
    Args:
        mac_addresses (list): List of MAC address strings (format "XX:XX:XX:XX:XX:XX")
        user_agent (str): Custom User-Agent header (required by BeaconDB)
    
    Returns:
        dict: Location data with keys 'lat', 'lng', and 'accuracy'
    """
    url = "https://api.beacondb.net/v1/geolocate"
    headers = {"User-Agent": user_agent}
    wifiAccessPoints = []
    for network in networks:
        wifiAccessPoint = {"macAddress": network['bssid']}
        if 'signal_dbm' in network:
            wifiAccessPoint["signalStrength"] = int(network['signal_dbm'])
        wifiAccessPoints.append(wifiAccessPoint)
    payload = {
        "wifiAccessPoints": wifiAccessPoints
    }
    if verbose:
        print(f"beacondb payload:\n{payload}\n")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None



if __name__ == '__main__':
    networks = scan_wifi()
    print(f"Wifi scan returned {len(networks)} wifi networks.\n")
    if _VERBOSE_:
        SSIDs = ",".join([network["ssid"] for network in networks])
        print(f"SSIDs:\n{SSIDs}\n")

    result = locate_with_beacondb(networks, verbose=_VERBOSE_)
    if _VERBOSE_:
        print(f"beacondb response json:\n{result}\n")

    if result:
        print("Location found:")
        print(f"Latitude: {result['location']['lat']}")
        print(f"Longitude: {result['location']['lng']}")
        accuracy = result.get('accuracy', 'N/A')
        print(f"Accuracy: {accuracy} meters")
        geo_uri = f"https://www.openstreetmap.org/?geouri=geo:{result['location']['lat']},{result['location']['lng']}"
        if accuracy != "N/A":
            geo_uri += f";u={accuracy}"
        print(geo_uri)
    else:
        print("Location not found")
