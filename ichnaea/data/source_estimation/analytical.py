
from shapely import Polygon, Point

from shapely.ops import transform
from pyproj import Transformer

import numpy as np
from scipy.optimize import minimize
from pyproj import Transformer


inv_transformer = Transformer.from_crs(
    "EPSG:3857", "EPSG:4326", always_xy=True
)


class RouterMLE:

    def _transform_buildings(self, buildings: list[Polygon]):
        # get the top 5 buildings closest to the mean
        mean_lat = sum(m[0] for m in self.measurements) / len(self.measurements)
        mean_lon = sum(m[1] for m in self.measurements) / len(self.measurements)

        mean_point = Point(mean_lon, mean_lat)

        buildings_sorted = sorted(
            buildings,
            key=lambda b: b.distance(mean_point)
        )

        # keep top 5
        top5_buildings = buildings_sorted[:5]

        # transform to meters
        # transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
        return top5_buildings

    def __init__(self, measurements, building_boxes: list[Polygon]):
        self.measurements = measurements
        # self.buildings = building_boxes
        self.buildings = self._transform_buildings(building_boxes)
        self.points = []

        # GPS → metric projection
        self.transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        )

        self.obs = []

        for lat, lon, rssi in measurements:
            x, y = self.transformer.transform(lon, lat)
            self.obs.append((x, y, rssi))

        self.obs = np.array(self.obs)

        self.A = -40
        self.n = 2.7
        self.sigma = 6
        self.out_of_building_pen = -50

    def predict_rssi(self, router_pos, obs):
        dx = router_pos[0] - obs[0]
        dy = router_pos[1] - obs[1]

        d = np.sqrt(dx * dx + dy * dy) + 1e-6

        return self.A - 10 * self.n * np.log10(d)

    def inside_building(self, lat, lon):
        p = Point(lon, lat)
        for polygon in self.buildings:
            # print(polygon)
            # print(p)
            if polygon.covers(p):
                return True
        return False

    def cost(self, router_xy):
        error = 0
        self.points.append(inv_transformer.transform(*router_xy))

        for x, y, rssi in self.obs:
            pred = self.predict_rssi(router_xy, (x, y))
            error += (pred - rssi) ** 2

        # convert candidate back to lat/lon
        lon, lat = self.transformer.transform(
            router_xy[0], router_xy[1], direction="INVERSE"
        )

        # building prior
        if not self.inside_building(lat, lon):
            error += self.out_of_building_pen  # penalty

        return error

    def solve(self):
        xs = self.obs[:, 0]
        ys = self.obs[:, 1]

        start = [np.mean(xs), np.mean(ys)]

        res = minimize(
            self.cost,
            start,
            method="L-BFGS-B"
        )

        x, y = res.x

        lon, lat = self.transformer.transform(
            x, y,
            direction="INVERSE"
        )

        return lat, lon

# got to try the method with multiple initial points for optimization...
# just pick a point in any of the buildings + at the average, which can be outside the buildings.


class MultipleStartsMLE(RouterMLE):

    def average_obs(self):
        xs = self.obs[:, 0]
        ys = self.obs[:, 1]

        return (np.mean(xs), np.mean(ys))

    def buildings_positions(self):
        return [self.transformer.transform(*building.point_on_surface().coords[0]) for building in self.buildings]

    def solve(self):
        self.out_of_building_pen = 75
        starts = [self.average_obs()] + self.buildings_positions()
        results = []
        # print("AAA", starts)
        for start in starts:
            res = minimize(
                self.cost,
                start,
                method="L-BFGS-B"
            )

            results.append(res)
            self.points.append(inv_transformer.transform(*start))

        best = min(results, key=lambda r: r.fun)

        x, y = best.x

        lon, lat = self.transformer.transform(
            x, y,
            direction="INVERSE"
        )

        return lat, lon
