#!/usr/bin/env python3

"""Test functions of the proximity.py file
"""
from collections.abc import Sequence
from unittest import TestCase, main
import warnings

import geopandas as gpd
from geopandas.testing import assert_geoseries_equal
import numpy as np
import pandas as pd
from shapely import Point

from danlab.geospatial.proximity import select_within_centroid

class TestSelectWithinCentroid(TestCase):
    """Tests that check select_within_centroid
    """
    _rng: np.random.Generator
    _test_count = 0
    _WORLD_GEODESIC: str = "EPSG:4326"
    _ALBERTA_10TM: str = "EPSG:3402" # Alberta projection, in meters

    def setUp(self) -> None:
        """Set up variables between every test
        """
        self._rng = np.random.default_rng(seed=76654 + self._test_count) # new seed for every test
        self._test_count += 1
        return super().setUp()

    def _polar_to_cartesian(self, radii : np.typing.ArrayLike, angles: np.typing.ArrayLike) -> np.typing.NDArray:
        """Convert arrays of radii and polar angles to cartesian points

        Parameters
        ----------
        radii : np.typing.ArrayLike
            An array of radii from a reference point. Should be same length as angles
        angles : np.typing.ArrayLike
            An array of angles (polar). Should be same length as radii

        Returns
        -------
        np.typing.NDArray
            A list of points representing the radii/angles given in cartesian coordinates
        """
        cplx_cart = radii * np.exp(1j * angles) # points converted to cartesian, represented as complex values
        return np.array([Point(cart.real, cart.imag) for cart in cplx_cart])

    def _generate_points_within_distance(self,
                                         reference_lonlat: Point,
                                         distance: float | Sequence[float],
                                         num_pts : int,
                                         crs: str) -> gpd.GeoSeries:
        if isinstance(distance, (float, int)):
            distance = (0., distance)
        if not isinstance(distance, Sequence):
            raise ValueError(f"Unrecognized input for distance {type(distance)}. Please provide one number or iterable")

        radii = np.sqrt(self._rng.uniform(low=distance[0]**2, high=distance[1]**2, size=num_pts))
        angles = self._rng.uniform(low=0, high=2 * np.pi, size=num_pts)

        # get the reference point from lon/lat to CRS given
        ref_in_crs = gpd.GeoSeries(reference_lonlat, crs=self._WORLD_GEODESIC).to_crs(crs=crs)

        # take random polar coordinates, convert to cartesian in CRS, then move/translate to surround reference point
        pts_in_crs = gpd.GeoSeries(self._polar_to_cartesian(radii=radii, angles=angles), crs=crs)
        pts_in_crs = pts_in_crs.translate(ref_in_crs.iloc[0].x, ref_in_crs.iloc[0].y)

        # return points as lon/lat coordinates
        return pts_in_crs.to_crs(crs=self._WORLD_GEODESIC)

    def test_bad_input_types(self):
        """Test that function raises ValueError when input can't work
        """
        with self.assertRaises(ValueError):
            select_within_centroid(reference_lonlat=24, points_in_lonlat=[Point(42, 22)], distance=100, crs="WGS84")

        with self.assertRaises(ValueError):
            select_within_centroid(reference_lonlat=Point(100,100), points_in_lonlat=[1,2,3], distance=90, crs="WGS84")

        with self.assertRaises(ValueError):
            select_within_centroid(reference_lonlat=Point(50,20),
                                   points_in_lonlat=[Point(11,22), Point(30,100)],
                                   distance="rawr",
                                   crs=self._WORLD_GEODESIC)

    def test_all_outside(self):
        """Test what happens when there are no points that fall inside the distance
        """
        data_out = select_within_centroid(reference_lonlat=Point(-113.2, 53.8),
                                          points_in_lonlat=[Point(-113.1, 53.8), Point(-113.5, 53.9)],
                                          distance=10,
                                          crs=self._ALBERTA_10TM)
        self.assertTrue(data_out.empty)

    def test_degree_distance(self):
        """Test that the distance is in degrees
        """
        reference_point_lonlat = Point(-113.99, 50.778) # south of Calgary

        distance = 0.005 # degrees distance
        points_within = self._generate_points_within_distance(reference_lonlat=reference_point_lonlat,
                                                              distance=distance,
                                                              num_pts=150,
                                                              crs=self._WORLD_GEODESIC)
        points_outside = self._generate_points_within_distance(reference_lonlat=reference_point_lonlat,
                                                               distance=[distance, 50.],
                                                               num_pts=50,
                                                               crs=self._WORLD_GEODESIC)
        joined_points = pd.concat([points_within, points_outside])
        joined_points = joined_points.sample(frac=1) # shuffling points, so within and outside are mixed

        # We get a nice warning about distance being in degrees here; disable for test
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            data_out = select_within_centroid(reference_lonlat=reference_point_lonlat,
                                            points_in_lonlat=joined_points,
                                            distance=distance,
                                            crs=self._WORLD_GEODESIC)

        assert_geoseries_equal(data_out.sort_index(), points_within)

    def test_distance_meters(self):
        """Test when distance is in meters
        """
        reference_point_lonlat = Point(-114.7, 51.2) # north-west of Calgary

        distance = 30.
        points_within = self._generate_points_within_distance(reference_lonlat=reference_point_lonlat,
                                                              distance=distance,
                                                              num_pts=200,
                                                              crs=self._ALBERTA_10TM)
        points_outside = self._generate_points_within_distance(reference_lonlat=reference_point_lonlat,
                                                               distance=[distance, 50.],
                                                               num_pts=100,
                                                               crs=self._ALBERTA_10TM)
        joined_points = pd.concat([points_within, points_outside])
        joined_points = joined_points.sample(frac=1) # shuffling points, so within and outside are mixed

        data_out = select_within_centroid(reference_lonlat=reference_point_lonlat,
                                          points_in_lonlat=joined_points,
                                          distance=distance,
                                          crs=self._ALBERTA_10TM)

        assert_geoseries_equal(data_out.sort_index(), points_within)


if __name__ == "__main__":
    main()
