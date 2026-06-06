from shapely import Polygon, Point

from shapely.ops import transform
from pyproj import Transformer

import numpy as np


class RouterLocator:

    def __init__(self, measurements: list[float, float, int], particles=8000):
        self.measurements = measurements
        self.n = particles

        # convert GPS → meters
        self.transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        )

        xs = []
        ys = []

        for lat, lon, rssi in measurements:
            x, y = self.transformer.transform(lon, lat)
            xs.append(x)
            ys.append(y)

        self.obs = np.column_stack([xs, ys])
        self.rssi = np.array([m[2] for m in measurements])

        # search area
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)

        margin = 100

        self.xlim = (xmin - margin, xmax + margin)
        self.ylim = (ymin - margin, ymax + margin)

        # initialize particles
        self.particles = np.empty((self.n, 2))

        self.particles[:, 0] = np.random.uniform(*self.xlim, self.n)
        self.particles[:, 1] = np.random.uniform(*self.ylim, self.n)

        self.weights = np.ones(self.n) / self.n

    def predict_rssi(self, particle, observer):
        A = -40      # RSSI at 1m
        n = 2.7      # path loss exponent

        dx = particle[0] - observer[0]
        dy = particle[1] - observer[1]

        d = np.sqrt(dx * dx + dy * dy) + 1e-6

        return A - 10 * n * np.log10(d)

    def update(self):
        sigma = 6

        for i in range(self.n):
            likelihood = 1

            for obs, rssi in zip(self.obs, self.rssi):
                pred = self.predict_rssi(self.particles[i], obs)
                error = pred - rssi
                likelihood *= np.exp(-(error**2) / (2 * sigma**2))

            self.weights[i] = likelihood

        self.weights += 1e-300
        self.weights /= np.sum(self.weights)

    def resample(self):
        idx = np.random.choice(
            self.n,
            self.n,
            p=self.weights
        )

        self.particles = self.particles[idx]

        self.weights.fill(1 / self.n)

        # jitter
        self.particles += np.random.normal(0, 2, self.particles.shape)

    def run(self, iterations=6):
        for _ in range(iterations):
            self.update()
            self.resample()

        estimate = np.mean(self.particles, axis=0)

        # convert back to lat lon
        lon, lat = self.transformer.transform(
            estimate[0], estimate[1], direction="INVERSE"
        )

        return lat, lon


class RouterLocatorWithBiasToBuildings(RouterLocator):

    def __init__(self, measurements: list[float, float, float], buildings_polygons: list[Polygon], particles=8000):
        # get the top 5 buildings closest to the mean
        mean_lat = sum(m[0] for m in measurements) / len(measurements)
        mean_lon = sum(m[1] for m in measurements) / len(measurements)

        mean_point = Point(mean_lon, mean_lat)

        buildings_sorted = sorted(
            buildings_polygons,
            key=lambda b: b.distance(mean_point)
        )

        # keep top 5
        top5_buildings = buildings_sorted[:5]

        # transform to meters
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
        self.buildings = [transform(transformer, b) for b in top5_buildings]

        super().__init__(measurements, particles)

    def in_building(self, point: tuple[float, float]):
        for polygon in self.buildings:
            if polygon.covers(Point(*point)):
                return True
        return False

    def update(self):
        sigma = 6

        for i in range(self.n):
            point = self.particles[i]
            likelihood = 1 if self.in_building(point) else 0.1

            for obs, rssi in zip(self.obs, self.rssi):
                pred = self.predict_rssi(point, obs)
                error = pred - rssi
                likelihood *= np.exp(-(error**2) / (2 * sigma**2))

            self.weights[i] = likelihood

        self.weights += 1e-300
        self.weights /= np.sum(self.weights)
