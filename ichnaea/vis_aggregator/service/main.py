from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from shapely.geometry import Point
from starlette.middleware.cors import CORSMiddleware

from ichnaea.models import SubmittedReport
from ichnaea.vis_aggregator.service.observations import (
    Tile,
    ObservationsCrawler,
    DiscoveredWifiCrawler,
    DiscoveredCellCrawler,
    DiscoveredBlueCrawler,
)

observations_crawler = ObservationsCrawler()
wifi_crawler = DiscoveredWifiCrawler()
cell_crawler = DiscoveredCellCrawler()
blue_crawler = DiscoveredBlueCrawler()


app = FastAPI(title="Observations Debug API")

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Request models
# -------------------------

class TileRequest(BaseModel):
    lat: float
    lon: float
    size: float  # degrees


# -------------------------
# Response models
# -------------------------

class SubmittedReportOut(BaseModel):
    id: int
    api_key: str | None
    lat: float
    lon: float
    source: str | None
    report: str
    created: str

    @classmethod
    def from_orm(cls, obj: SubmittedReport):
        return cls(
            id=obj.id,
            api_key=obj.api_key,
            lat=obj.lat,
            lon=obj.lon,
            source=obj.source,
            report=obj.report,
            created=obj.created.isoformat(),
        )


class TransmitterOut(BaseModel):
    lat: float
    lon: float
    bssid: str
    weight: float

    @classmethod
    def from_orm(cls, obj):
        return cls(lat=obj.lat, lon=obj.lon, bssid=obj.mac, weight=obj.weight)




# -------------------------
# Helpers
# -------------------------

def tile_from_request(req: TileRequest) -> Tile:
    center = Point(req.lat, req.lon)
    return Tile.from_square_box(center=center, size=req.size)


# -------------------------
# Endpoints
# -------------------------

@app.post("/observations", response_model=List[SubmittedReportOut])
def get_observations(req: TileRequest):
    tile = tile_from_request(req)

    rows = observations_crawler.fetch_for_tile(tile)
    return [SubmittedReportOut.from_orm(r) for r in rows]


@app.post("/wifi", response_model=List[TransmitterOut])
def get_wifi_transmitters(req: TileRequest):
    tile = tile_from_request(req)

    rows = wifi_crawler.fetch_for_tile(tile)
    return [TransmitterOut.from_orm(r) for r in rows]


@app.post("/cell", response_model=List[TransmitterOut])
def get_cell_transmitters(req: TileRequest):
    tile = tile_from_request(req)

    rows = cell_crawler.fetch_for_tile(tile)
    return [TransmitterOut.from_orm(r) for r in rows]


@app.post("/bluetooth", response_model=List[TransmitterOut])
def get_bluetooth_transmitters(req: TileRequest):
    tile = tile_from_request(req)

    rows = blue_crawler.fetch_for_tile(tile)
    return [TransmitterOut.from_orm(r) for r in rows]
