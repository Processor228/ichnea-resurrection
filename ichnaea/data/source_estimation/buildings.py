import osmnx as ox
from functools import lru_cache


class BuildingsSource:
    """
       This class is supposed to handle buildings polugons querries.
       Perhaps, with some caching, and certain coordinate transformation.
       Yet, this project is just a prototype for now, and it can only
       return innopolis buildings.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def innopolis_buildings():
        return ox.features_from_point(
            (55.74962338088823, 48.74653394564308),
            {"building": True},
            1000
        ).geometry
