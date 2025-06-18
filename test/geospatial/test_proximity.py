#!/usr/bin/env python3

"""Test functions of the proximity.py file
"""
from collections.abc import Sequence
from numbers import Real
from unittest import TestCase, main
import warnings

import geopandas as gpd
from geopandas.testing import assert_geoseries_equal
import numpy as np
import pandas as pd
from shapely import Point, Polygon, MultiPolygon

from danlab.geospatial.proximity import select_within_centroid, select_within_distance_of_region

class TestProximity(TestCase):
    """Base Test class for Proximity file

    Sets up the geo landscape
    """
    _rng: np.random.Generator
    _test_count = 0
    _WORLD_GEODESIC: str = "EPSG:4326"
    _ALBERTA_10TM: str = "EPSG:3402" # Alberta projection, in meters

    def setUp(self) -> None:
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
                                         distance: Real | Sequence[Real],
                                         num_pts : int,
                                         crs: str) -> gpd.GeoSeries:
        """Generate points within a distance of a reference point

        Parameters
        ----------
        reference_lonlat : Point
            Reference point in longitude and latitude
        distance : Real | Sequence[Real]
            Distances from the reference point to generate the points. If a
            single value given, it is the max distance of the point from the
            reference. If two points given, min and max distance from reference
        num_pts : int
            Number of points to generate
        crs : str
            The CRS to treat the distance and to convert the reference point to

        Returns
        -------
        gpd.GeoSeries
            A series of points within the specified distance from the reference
            point, in longitude and latitude

        Raises
        ------
        ValueError
            The distance given was not a real number or a sequence
        """
        if isinstance(distance, Real):
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


class TestSelectWithinCentroid(TestProximity):
    """Tests that check select_within_centroid
    """
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

class TestSelectWithinDistanceOfRegion(TestProximity):
    """Testing select_within_distance_of_region
    """
    def _generate_points_around_region(self,
                                       region_lonlat: Polygon,
                                       num_pts: int,
                                       distance: Real | Sequence[Real],
                                       crs:str) -> gpd.GeoSeries:
        if isinstance(distance, Real):
            distance = (0, distance)
        if not isinstance(distance, Sequence):
            raise ValueError("Distance must be either a real number or two real numbers representing a min, max")

        region_in_crs = gpd.GeoSeries(region_lonlat, crs=self._WORLD_GEODESIC).to_crs(crs=crs)
        inner_buffer = region_in_crs.buffer(distance=distance[0]).iloc[0] # polygon represent inner side of buffer
        outer_buffer = region_in_crs.buffer(distance=distance[1]).difference(inner_buffer).iloc[0] # buffer polygon

        # find the min/max range of the buffer created above
        region_centroid = region_in_crs.iloc[0].centroid
        min_radius = region_centroid.distance(inner_buffer.boundary)
        outer_buffer_pts = gpd.GeoSeries([Point(pt[0], pt[1]) for pt in outer_buffer.exterior.coords])
        max_radius = outer_buffer_pts.distance(region_centroid).max()

        pts_out = gpd.GeoSeries([])
        while len(pts_out) < num_pts:
            # generate a extra points in a circle surrounding buffer. Not all will fall in buffer
            pts_sample = self._generate_points_within_distance(region_lonlat.centroid,
                                                               distance=(min_radius, max_radius),
                                                               num_pts=num_pts*300,
                                                               crs=crs)
            pts_sample = pts_sample.to_crs(crs=crs)
            pts_in_buf = pts_sample[pts_sample.within(outer_buffer)]
            pts_out = pd.concat([pts_out, pts_in_buf])[:num_pts]

        return pts_out.to_crs(self._WORLD_GEODESIC)

    def test_bad_input_types(self):
        """Test if bad inputs fail gracefully
        """
        valid_polygon = Polygon([(-110., 40.), (-110.03, 40.03), (-110.08, 40.034), (-110., 40.)])
        valid_points = gpd.GeoSeries([Point(-110.04, 39.97), Point(-110.13, 40.11)])
        valid_distance = 10.2

        # A bad polygon
        with self.assertRaises(ValueError):
            select_within_distance_of_region(region=30,
                                             points=valid_points,
                                             distance=valid_distance)

        # A bad list of points
        with self.assertRaises(ValueError):
            select_within_distance_of_region(region=valid_polygon,
                                             points="hey, I'm a point",
                                             distance=valid_distance)

        # A bad distance
        with self.assertRaises(ValueError):
            select_within_distance_of_region(region=valid_polygon,
                                             points=valid_points,
                                             distance=np.array([3,4,3]))

    def test_within_polygon(self):
        """See what happens when points are within the polygon
        """
        # decided to use a real life polygon for this test, Red Rock Natural Area
        red_rock_na = Polygon([(-110.873962, 49.662087), (-110.862755, 49.662072), (-110.862783, 49.654839),
                               (-110.862504, 49.654839), (-110.851383, 49.654828), (-110.851382, 49.647614),
                               (-110.862512, 49.647625), (-110.862791, 49.647625), (-110.873980, 49.647632),
                               (-110.885177, 49.647637), (-110.885177, 49.654856), (-110.885161, 49.662101),
                               (-110.873962, 49.662087)])

        # pick a few points around the centroid of the Red Rock Natural Area
        pts_within_region = self._generate_points_within_distance(reference_lonlat=red_rock_na.centroid,
                                                                  num_pts=25,
                                                                  distance=20,
                                                                  crs=self._ALBERTA_10TM)

        pts_out = select_within_distance_of_region(region=red_rock_na,
                                                   points=pts_within_region,
                                                   distance=1., # something small. All should be accepted regardless
                                                   crs=self._ALBERTA_10TM)

        assert_geoseries_equal(pts_within_region, pts_out)

    def test_polygon_distance_meters(self):
        """Generate points within distance from polygon and outside distance
        """
        # A small portion of Dinosaur Provincial Park
        dinosaur_pp = Polygon([(-111.582009, 50.792988), (-111.582193, 50.792937), (-111.583284, 50.792983),
                               (-111.584389, 50.793175), (-111.584534, 50.793272), (-111.584947, 50.79376),
                               (-111.585028, 50.793906), (-111.585141, 50.794029), (-111.585691, 50.79439),
                               (-111.586344, 50.794818), (-111.58713, 50.795447), (-111.587265, 50.795585),
                               (-111.586504, 50.795621), (-111.586289, 50.795579), (-111.586123, 50.795498),
                               (-111.585857, 50.795298), (-111.585691, 50.795207), (-111.585382, 50.795036),
                               (-111.583609, 50.794251), (-111.583287, 50.794046), (-111.582226, 50.793232),
                               (-111.582102, 50.793115), (-111.582009, 50.792988)])
        distance = 100 # meters

        pts_within = self._generate_points_around_region(region_lonlat=dinosaur_pp,
                                                         num_pts=200,
                                                         distance=distance,
                                                         crs=self._ALBERTA_10TM)
        pts_outside = self._generate_points_around_region(region_lonlat=dinosaur_pp,
                                                          num_pts=100,
                                                          distance=[distance, distance + 200],
                                                          crs=self._ALBERTA_10TM)
        pts_combined = pd.concat([pts_within, pts_outside])
        pts_combined = pts_combined.sample(frac=1) # shuffle so not all inside pts are together
        pts_out = select_within_distance_of_region(region=dinosaur_pp,
                                                   points=pts_combined,
                                                   distance=distance,
                                                   crs=self._ALBERTA_10TM)

        assert_geoseries_equal(pts_out.sort_index(), pts_within)

    def test_multi_polygon_distance_meters(self):
        """Give a MultiPolygon as input and test some points around it
        """
        # Take the multi-polygon of cow lake
        cow_lake_na = MultiPolygon([Polygon([(-115.001386, 52.3034), (-115.001424, 52.290124), (-115.005755, 52.290114),
                                             (-115.008845, 52.291478), (-115.012842, 52.292449),
                                             (-115.019074, 52.292596), (-115.022579, 52.292155),
                                             (-115.02493, 52.291361), (-115.025868, 52.290818),
                                             (-115.026799, 52.289869), (-115.026925, 52.289357),
                                             (-115.027156, 52.289121), (-115.027097, 52.288669), (-115.02765, 52.28693),
                                             (-115.027658, 52.282646), (-115.03714, 52.282637),
                                             (-115.037158, 52.294715), (-115.029725, 52.297274),
                                             (-115.025106, 52.297281), (-115.025106, 52.297645),
                                             (-115.019341, 52.297738), (-115.016647, 52.298152), (-115.003, 52.303716),
                                             (-115.003001, 52.303403), (-115.001386, 52.3034)]),
                                    Polygon([(-115.108574, 52.289968),  (-115.120356, 52.289949),
                                             (-115.120362, 52.297174),  (-115.109298, 52.297178),
                                             (-115.10858, 52.297178),  (-115.107861, 52.297178),
                                             (-115.096807, 52.297181),  (-115.096809, 52.289985),
                                             (-115.108574, 52.289968)])])
        distance = 200

        pts_within = [self._generate_points_around_region(region_lonlat=poly,
                                                          num_pts=30,
                                                          distance=distance,
                                                          crs=self._ALBERTA_10TM) for poly in cow_lake_na.geoms]
        pts_within = pd.concat(pts_within, ignore_index=True)
        pts_outside = [self._generate_points_around_region(region_lonlat=poly,
                                                          num_pts=20,
                                                          distance=[distance, distance + 300],
                                                          crs=self._ALBERTA_10TM) for poly in cow_lake_na.geoms]
        pts_outside = pd.concat(pts_outside, ignore_index=True)

        pts_combined = pd.concat([pts_within, pts_outside]).sample(frac=1)

        pts_out = select_within_distance_of_region(region=cow_lake_na,
                                                   points=pts_combined,
                                                   distance=distance,
                                                   crs=self._ALBERTA_10TM)

        assert_geoseries_equal(pts_out.sort_index(), pts_within)

if __name__ == "__main__":
    main()
