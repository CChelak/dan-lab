#!/usr/bin/env python3

"""Test functions found in danlab/api/hourly_data.py
"""
from datetime import datetime
from collections.abc import Iterable
from unittest import TestCase, main

import geopandas as gpd
import pandas as pd
import responses
from shapely import Point

from danlab.api.hourly_data import request_hourly_data

class TestRequestHourlyData(TestCase):
    """Unit test request_hourly_data function
    """
    _hourly_url = "https://api.weather.gc.ca/collections/climate-hourly/items"
    _hourly_queryable = "https://api.weather.gc.ca/collections/climate-hourly/queryables"

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
            url = self._hourly_queryable,
            match = [responses.matchers.query_param_matcher({'f':'json'}, strict_match=False)],
            json = queryable_json,
            status = 200
        )

        # For the number matched check
        responses.get(
            url = self._hourly_url,
            match = [responses.matchers.query_param_matcher({'f': 'json', 'limit': 1, 'offset': 0},
                                                            strict_match=False)],
            json = {'numberMatched': number_matched},
            status = 200
        )

    @responses.activate
    def test_bad_input(self):
        """Test if we catch bad inputs early
        """

        # pass some silly station ids
        with self.assertRaises(TypeError):
            request_hourly_data(station_id='boy oh boy', properties=['STN_ID'])

        # Any ole object to station id
        with self.assertRaises(TypeError):
            request_hourly_data(station_id=TestCase, properties=['TEMP'])

        # pass some silly properties
        with self.assertRaises(TypeError):
            request_hourly_data(station_id=1, properties=11)

        # Will this cry when we don't pass a string in iterable?
        with self.assertRaises(TypeError):
            request_hourly_data(station_id=3, properties=['DOG', 3+2j])

        # pass a silly date interval
        with self.assertRaises(TypeError):
            request_hourly_data(station_id=2, properties=['LOCAL_DAY'], date_interval=12)

    @responses.activate
    def test_unqueryable_removed(self):
        """Test if we remove/ignore unqueryable properties
        """
        valid_properties = ['LOCAL_HOUR', 'ID']
        self._make_initial_check_responses(properties=valid_properties, number_matched=1)

        responses.get(
            url = self._hourly_url,
            json = {"type":"FeatureCollection",
                    "numberReturned":1,
                    "features":[{"id":"ABCDEF",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-123,49]},
                                 "properties":{"LOCAL_HOUR":"11",
                                               "ID":"ABCDEF"}}]},
            match = [responses.matchers.query_param_matcher({'properties':','.join(valid_properties)},
                                                            strict_match=False)],
            status = 200
        )

        output = request_hourly_data(station_id=50, properties=['LOCAL_HOUR', 'BAD', 'ID'])

        # comes with id, geometry, and two requested property columns
        self.assertEqual(output.columns.size, 4)

        # These are almost redundant to the response library checks
        for prop in valid_properties:
            self.assertIn(member=prop, container=output.columns)

        # ensure that the bad property did not make its way out of the response
        self.assertNotIn(member='BAD', container=output.columns)

    @responses.activate
    def test_return_early_no_match(self):
        """Test if we return early when we find that there are no API matches
        """
        test_properties = ['LOCAL_YEAR']
        self._make_initial_check_responses(properties=test_properties, number_matched=0)

        data_out = request_hourly_data(station_id=123,
                                      date_interval=datetime(year=1992, month=10, day=2),
                                      properties=test_properties)
        pd.testing.assert_frame_equal(data_out, gpd.GeoDataFrame())

    @responses.activate
    def test_multi_request(self):
        """Test if we get all information from multiple data requests
        """
        test_properties = ['TEMP']
        self._make_initial_check_responses(properties=test_properties, number_matched=2)

        # have the responses spit out one row at a time
        responses.get(
            url = self._hourly_url,
            json = {"type":"FeatureCollection",
                    "features":[{"id":"3057376.2015.5.19.10",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-115.78666666666666,54.14388888888889]},
                                 "properties":{"TEMP":15.8}}],
                    "numberMatched":2,
                    "numberReturned":1},
            status = 200
        )

        responses.get(
            url = self._hourly_url,
            json = {"type":"FeatureCollection",
                    "features":[{"id":"3057376.2015.5.19.13",
                                 "type":"Feature",
                                 "geometry":{"type":"Point","coordinates":[-115.78666666666666,54.14388888888889]},
                                 "properties":{"TEMP":18.9}}],
                    "numberMatched":2,
                    "numberReturned":1},
            status = 200
        )

        # setting the limit to 1 should cause two requests to happen, one for each row
        data_out = request_hourly_data(station_id=52982,
                                      properties=test_properties,
                                      limit=1)


        expected_out = gpd.GeoDataFrame({'id': ["3057376.2015.5.19.10","3057376.2015.5.19.13"],
                                         'geometry': [Point(-115.78666666666666,54.14388888888889)] * 2,
                                         'TEMP': [15.8, 18.9]
                                         })

        pd.testing.assert_frame_equal(data_out, expected_out)

class TestRequestHourlyDataIntegration(TestCase):
    """Testing actual API calls for request_hourly_data"""

if __name__ == "__main__":
    main()
