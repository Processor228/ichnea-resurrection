from dataclasses import dataclass
from typing import Iterable, List, Type

from shapely.geometry import Point
from sqlalchemy.orm import Session

from ichnaea.db import configure_db, db_worker_session
from ichnaea.models import (
    SubmittedReport,
    WifiShard,
    BlueShard,
    CellShard,
)


@dataclass(frozen=True)
class Tile:
    """Geographic bounding box, represents a tile
       on a possible frontend application.
    """
    luc: Point  # left-upper corner
    rdc: Point  # right-down corner

    @property
    def bounds(self):
        """
        Returns (lat_min, lat_max, lon_min, lon_max)
        """
        lat_min = self.luc.x
        lat_max = self.rdc.x
        lon_min = self.rdc.y
        lon_max = self.luc.y
        return lat_min, lat_max, lon_min, lon_max

    @staticmethod
    def from_square_box(center: Point, size: float) -> "Tile":
        half = size / 2
        return Tile(
            luc=Point(center.x - half, center.y + half),
            rdc=Point(center.x + half, center.y - half),
        )


class BaseCrawler:
    def __init__(self):
        self.db = configure_db("ro", pool=False)

    def _session(self):
        return db_worker_session(self.db, commit=False)


# -------------------------
# Observations crawler should also be sharded. but leave this as
# thechdebt for now.

class ObservationsCrawler(BaseCrawler):

    def fetch_for_tile(self, tile: Tile) -> List[SubmittedReport]:
        lat_min, lat_max, lon_min, lon_max = tile.bounds

        with self._session() as session:
            return (
                session.query(SubmittedReport)
                .filter(
                    SubmittedReport.lat.between(lat_min, lat_max),
                    SubmittedReport.lon.between(lon_min, lon_max),
                )
                .all()
            )


class ShardedCrawler(BaseCrawler):
    """
    Base class for shard-backed transmitter crawlers.
    """

    shard_models: Iterable[Type]

    def fetch_for_tile(self, tile: Tile):
        lat_min, lat_max, lon_min, lon_max = tile.bounds
        results = []

        with self._session() as session:
            for shard_cls in self.shard_models:
                results.extend(
                    self._query_shard(
                        session,
                        shard_cls,
                        lat_min,
                        lat_max,
                        lon_min,
                        lon_max,
                    )
                )

        return results

    @staticmethod
    def _query_shard(
        session: Session,
        shard_cls: Type,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
    ):
        return (
            session.query(shard_cls)
            .filter(
                shard_cls.lat.between(lat_min, lat_max),
                shard_cls.lon.between(lon_min, lon_max),
            )
            .all()
        )


class DiscoveredWifiCrawler(ShardedCrawler):
    shard_models = WifiShard.shards().values()


class DiscoveredCellCrawler(ShardedCrawler):
    shard_models = CellShard.shards().values()


class DiscoveredBlueCrawler(ShardedCrawler):
    shard_models = BlueShard.shards().values()
