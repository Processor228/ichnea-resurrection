import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
from ichnaea.vis_aggregator.service.main import TransmitterOut, SubmittedReportOut

st.set_page_config(page_title="ALS", layout="wide")

URL = "http://visual-service:8080"
CENTER_LAT, CENTER_LON = 55.747640, 48.742494
SQUARE_SZ = 1


# ---------------- API calls ----------------
def query_wifi(lat, lon, square_sz) -> list[TransmitterOut]:
    r = requests.post(
        f"{URL}/wifi",
        json={"lat": lat, "lon": lon, "size": square_sz},
        headers={"Content-Type": "application/json"},
        timeout=2,
    )
    print(r.text)

    r.raise_for_status()
    return r.json()


def query_observations(lat, lon, square_sz) -> list[SubmittedReportOut]:
    r = requests.post(
        f"{URL}/observations",
        json={"lat": lat, "lon": lon, "size": square_sz},
        headers={"Content-Type": "application/json"},
        timeout=2,
    )
    r.raise_for_status()
    return r.json()


# ---------------- Controls ----------------
if st.button("🔄 Refresh"):
    st.experimental_rerun()

# ---------------- Fetch data ----------------
try:
    wifis = query_wifi(CENTER_LAT, CENTER_LON, SQUARE_SZ)
    observations = query_observations(CENTER_LAT, CENTER_LON, SQUARE_SZ)
except Exception as e:
    st.error(str(e))
    wifis, observations = [], []

# ---------------- Map ----------------
m = folium.Map(
    location=[CENTER_LAT, CENTER_LON],
    zoom_start=20,
    tiles="OpenStreetMap",
)

folium.Marker(
    [CENTER_LAT, CENTER_LON],
    tooltip="My office...",
    icon=folium.Icon(color="blue"),
).add_to(m)

# ---- WiFi transmitters ----
for w in wifis:
    folium.CircleMarker(
        [w["lat"], w["lon"]],
        radius=3,
        color="green",
        fill=True,
        fill_opacity=0.9,
        tooltip=w["bssid"],
    ).add_to(m)

# ---- Observations ----
for o in observations:
    folium.CircleMarker(
        [o["lat"], o["lon"]],
        radius=5,
        color="red",
        fill=True,
        fill_opacity=0.8,
        tooltip=f"id={o['id']} src={o['source']}",
    ).add_to(m)

# ---------------- Render ----------------
st_folium(m, width=1200, height=700)

st.caption(
    f"WiFi: {len(wifis)} | Observations: {len(observations)}"
)
