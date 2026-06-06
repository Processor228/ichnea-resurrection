from typing import Iterable
import math
import random

from pyproj import CRS, Transformer
from scipy.optimize import least_squares
import numpy as np


class APStimater:

    def __init__(self, observations: Iterable[tuple[float, float, int]]):
        self.obs = observations

        # initial learned params
        self.n = 2.0
        self.A = -45.0
        self.lat = sum(o[0] for o in self.obs) / len(self.obs)
        self.lon = sum(o[1] for o in self.obs) / len(self.obs)

        local_crs = CRS.from_proj4(
            f"+proj=aeqd +lat_0={self.lat} +lon_0={self.lon} +datum=WGS84 +units=m +no_defs"
        )

        self.to_xy = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
        self.to_ll = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True)

        # project all measurements into meters
        self.xy_obs = []
        for lat, lon, rssi in self.obs:
            x, y = self.to_xy.transform(lon, lat)
            self.xy_obs.append((x, y, rssi))

        self.trust = 1e15

    @staticmethod
    def _predict_rssi(A: float, n: float, d: float) -> float:
        d = max(d, 1.0)
        return A - 10.0 * n * math.log10(d)

    def _residuals(self, params):
        x_ap, y_ap, A, n = params

        out = []

        for x, y, rssi in self.xy_obs:
            d = math.hypot(x - x_ap, y - y_ap)
            pred = self._predict_rssi(A, n, d)

            err = pred - rssi

            out.append(err)

        # soft regularization toward plausible RF values
        out.append((A + 44.0) * 0.7)
        out.append((n - 2.2) * 3.0)

        return np.array(out)

    def estimate(self) -> tuple[float, float, float, float]:

        x0 = np.array([
            0.0,
            0.0,
            -40,
            2.2
        ])

        bounds_lower = np.array([
            -120.0,
            -120.0,
            -55.0,
            1.2
        ])

        bounds_upper = np.array([
            120.0,
            120.0,
            -30.0,
            4.5
        ])

        result = least_squares(
            self._residuals,
            x0=x0,
            bounds=(bounds_lower, bounds_upper),
            loss="soft_l1",
            f_scale=5.0,
            max_nfev=2000,
        )

        print(f"success={result.success} cost={result.cost}")
        if not result.success or result.cost > 500:
            print("Unsuccessful estimation")
            self.estimate_with_fixed_path_loss(-45, 2.7)
            return

        x_ap, y_ap, A, n = result.x

        lon_ap, lat_ap = self.to_ll.transform(x_ap, y_ap)

        self.x_ap = x_ap
        self.y_ap = y_ap
        self.lat = lat_ap
        self.lon = lon_ap
        self.A = A
        self.n = n

        return lat_ap, lon_ap, A, n

    def estimate_with_fixed_path_loss(self, A, n) -> tuple[float, float, float, float]:
        x0 = np.array([
            0.0,
            0.0,
        ])

        bounds_lower = np.array([
            -120.0,
            -120.0,
        ])

        bounds_upper = np.array([
            120.0,
            120.0,
        ])

        def residuals_with_captured_params(params):
            x_ap, y_ap = params

            out = []

            for x, y, rssi in self.xy_obs:
                d = math.hypot(x - x_ap, y - y_ap)
                pred = APStimater._predict_rssi(A, n, d)

                err = pred - rssi

                out.append(err)

            return np.array(out)

        result = least_squares(
            residuals_with_captured_params,
            x0=x0,
            bounds=(bounds_lower, bounds_upper),
            loss="soft_l1",
            f_scale=5.0,
            max_nfev=2000,
        )

        x_ap, y_ap = result.x

        lon_ap, lat_ap = self.to_ll.transform(x_ap, y_ap)

        self.x_ap = x_ap
        self.y_ap = y_ap
        self.lat = lat_ap
        self.lon = lon_ap
        self.A = A
        self.n = n

        return lat_ap, lon_ap, A, n

    def radius(self, rssi: float) -> float:
        """
        Returns estimated distance in meters using learned path loss params
        """
        return 10 ** ((self.A - rssi) / (10.0 * self.n))
