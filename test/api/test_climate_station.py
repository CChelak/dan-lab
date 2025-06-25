#!/usr/bin/env python3

"""Tests for the climate_station API module
"""
from collections.abc import Iterable
from unittest import TestCase, main

import geopandas as gpd
import pandas as pd
import responses
from shapely import Point

from danlab.api.climate_station import request_climate_stations

class TestRequestClimateStations(TestCase):
    """Test the request_climate_stations function
    """
    _climate_station_url = "https://api.weather.gc.ca/collections/climate-stations/items"
    _climate_station_queryable = "https://api.weather.gc.ca/collections/climate-stations/queryables"

    def _make_initial_check_responses(self, properties: Iterable[str], number_matched: int = 1):
        """Add additional responses to the queue that check queryables and
        number matched

        Parameters
        ----------
        properties : Iterable[str]
            The queryable properties to include in the queryables response
        number_matched : int
            Number of matched to return to user, default is 1
        """
        # For when queryables is checked
        queryable_json = { "properties": { prop: {'title': prop, 'type': 'string'} for prop in properties } }

        responses.get(
            url = self._climate_station_queryable,
            match = [responses.matchers.query_param_matcher({'f':'json'}, strict_match=False)],
            json = queryable_json,
            status = 200
        )

        # For the number matched check
        responses.get(
            url = self._climate_station_url,
            match = [responses.matchers.query_param_matcher({'f': 'json', 'limit': 1, 'offset': 0},
                                                            strict_match=False)],
            json = {'numberMatched': number_matched},
            status = 200
        )

    @responses.activate
    def test_bad_input(self):
        """Test some bad properties types that it cannot process
        """
        # I'm not handling passing in a raw string yet. So I should be explicit
        string_property = "steve jeans"

        with self.assertRaises(ValueError):
            request_climate_stations(properties=string_property)

        # Nor can I pass in a real number or other non-iterables
        int_property = 42
        with self.assertRaises(ValueError):
            request_climate_stations(properties=int_property)

    @responses.activate
    def test_bad_property_exclusion(self):
        """Test that a bad property is reported and ignored
        """
        valid_properties = ["STN_ID", "COUNTRY", "FIRST_DATE"] # properties that were good at the time
        bad_properties = ["fish"]

        self._make_initial_check_responses(properties=valid_properties, number_matched=2)

        # A clip of the response that came from the actual API when constructing the tests
        responses.get(
            url = self._climate_station_url,
            json = {"type":"FeatureCollection",
                    "numberReturned":2,
                    "features":[{"id":"101AE00",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-123.7,48.916666666666664]},
                                 "properties":{"STN_ID":"2",
                                               "COUNTRY":"CAN",
                                               "FIRST_DATE":"1979-01-01 00:00:00"}},
                                {"id":"101C0ME",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-123.35,48.88333333333333]},
                                 "properties":{"STN_ID":"3",
                                               "COUNTRY":"CAN",
                                               "FIRST_DATE":"1979-01-01 00:00:00"}}]},
            match = [responses.matchers.query_param_matcher({'properties':','.join(valid_properties)},
                                                            strict_match=False)],
            status = 200
        )

        stations_out = request_climate_stations(properties=bad_properties + valid_properties, limit=2)

        # comes with id, geometry, and three requested property columns
        self.assertEqual(stations_out.columns.size, 5)

        # These are almost redundant to the response library checks
        for prop in valid_properties:
            self.assertIn(member=prop, container=stations_out.columns)

        # ensure that the bad property did not make its way out of the response
        self.assertNotIn(member=bad_properties[0], container=stations_out.columns)

    @responses.activate
    def test_join_multiple_requests(self):
        """Previously, I wasn't properly joining the dataframes of multiple requests

        This checks that each request made gets joined properly
        """
        properties_in = ['STATION_NAME']

        self._make_initial_check_responses(properties=properties_in, number_matched=2)
        responses.get(
            url = self._climate_station_url,
            json = {"type":"FeatureCollection",
                    "features":[{"id":"101F942",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-123.41666666666667,48.55]},
                                 "properties":{"STATION_NAME":"SAANICH OLDFIELD NORTH"}}],
                                 "numberReturned":1},
            match = [responses.matchers.query_param_matcher({'properties':','.join(properties_in)},
                                                            strict_match=False)],
            status = 200
                      )

        responses.get(
            url = self._climate_station_url,
            json = {"type":"FeatureCollection",
                    "features":[{"id":"101F942",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-123.26694444444445,48.455]},
                                 "properties":{"STATION_NAME":"VICTORIA PHYLLIS STREET"}}],
                                 "numberReturned":1},
            match = [responses.matchers.query_param_matcher({'properties':','.join(properties_in)},
                                                            strict_match=False)],
            status = 200
            )

        # with a limit of 1, should loop twice
        stations_out = request_climate_stations(properties=properties_in, limit=1)

        # are both station names found in the returned GeoDataFrame?
        self.assertTrue(stations_out['STATION_NAME'].str.contains('SAANICH OLDFIELD NORTH').any())
        self.assertTrue(stations_out['STATION_NAME'].str.contains('VICTORIA PHYLLIS STREET').any())

    @responses.activate
    def test_default_properties(self):
        """Test that the default properties argument will not result in error
        """
        # make the properties rather limited
        self._make_initial_check_responses(properties=['STN_ID'], number_matched=1)

        expected_out = gpd.GeoDataFrame({"id":["1041490"], "STN_ID":["302"], "geometry":[Point(123.15,49.8)]})

        # spit out a real station I got from an API request
        responses.get(
            url = self._climate_station_url,
            body = expected_out.to_json(),
            status = 200
            )

        # no arguments in, get a single station out
        stations_out = request_climate_stations()

        pd.testing.assert_frame_equal(stations_out, expected_out)


class TestRequestClimateStationsIntegration(TestCase):
    """Integration tests for request_climate_stations

    Does API calls, which means internet is needed to run these tests
    """

    def test_request_one_station(self):
        """Do a station request with a limit of 1. See that a station comes back
        """
        # Request only one station by ID, so I don't get all the database's stations for this little test
        stations_out = request_climate_stations(CLIMATE_IDENTIFIER='4041000')

        # confirm that we got a climate station
        self.assertEqual(stations_out.shape[0], 1)
        self.assertGreaterEqual(stations_out.columns.size, 2) # should at least have an id and geometry

    def test_bounding_box(self):
        """Given a small bounding box, get only a few stations back from API
        """
        # bounding box around Red Deer
        stations_out = request_climate_stations(bbox="-114.011868,52.207506,-113.605006,52.426595")

        # ensure we got a few stations out, but not all
        num_stations = stations_out.shape[0]
        self.assertLess(num_stations, 100)
        self.assertGreater(num_stations, 3)

        self.assertTrue(stations_out['STATION_NAME'].str.contains('Red Deer', case=False).any())

    def test_province_select(self):
        """Make sure province selection can work to narrow climate station requests
        """
        # Picking New Brunswick since it is geographically small
        stations_out = request_climate_stations(PROV_STATE_TERR_CODE='NB')

        self.assertTrue((stations_out['PROV_STATE_TERR_CODE'] == 'NB').all())

    def test_property_select(self):
        """Select only a few properties, and make sure the code respects that
        """
        # Pick a few properties to ask for
        properties = ['ELEVATION', 'LAST_DATE', 'ENG_PROV_NAME']
        stations_out = request_climate_stations(properties=properties, CLIMATE_IDENTIFIER='1010965')

        # expecting geometry and ID to be present
        self.assertLessEqual(stations_out.columns.difference(properties).size, 2)

        # check if all properties are present
        self.assertEqual(stations_out.columns.intersection(properties).size, len(properties))


if __name__ == "__main__":
    main()
