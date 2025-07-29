#!/usr/bin/env python3

"""Test the daily data functions and objects
"""
from collections.abc import Iterable
from datetime import datetime
import logging
from unittest import TestCase, main

import geopandas as gpd
from numpy import int32
import pandas as pd
import responses
from shapely import Point

from danlab.api.daily_data import request_data_frame, request_daily_data
from danlab.util.log_util import disable_all_logging

class TestRequestDataFrame(TestCase):
    """Unit test request_data_frame function
    """
    _daily_url = "https://api.weather.gc.ca/collections/climate-daily/items"

    @responses.activate
    def test_none_on_error(self):
        """Test that None is returned when an error occurs
        """
        responses.get(
            url = self._daily_url,
            body = "Error",
            status = 400
        )

        with disable_all_logging() as _:
            self.assertIsNone(request_data_frame(self._daily_url, params={}))

    @responses.activate
    def test_json_to_gdf(self):
        """Simulate a response of a json file and get the GeoDataFrame out
        """
        responses.get(
            url = self._daily_url,
            json = {"type":"FeatureCollection",
                    "numberReturned":2,
                    "features":[{"type":"Feature",
                                 "id":"40.1.2",
                                 "geometry":{"type":"Point","coordinates":[-123.6, 48.92]},
                                 "properties":{"a":0,
                                               "b":4}},
                                {"type":"Feature",
                                 "id":"40.1.2",
                                 "geometry":{"type":"Point","coordinates":[-123.6, 48.92]},
                                 "properties":{"a":1,
                                               "b":5}}]},
            status = 200
        )
        expected_out = gpd.GeoDataFrame({'id': ["40.1.2", "40.1.2"],
                                         'a': pd.Series([0, 1], dtype=int32),
                                         'b': pd.Series([4, 5], dtype=int32),
                                        'geometry': [Point(-123.6,48.92)] * 2 })

        pd.testing.assert_frame_equal(request_data_frame(self._daily_url, params={'f':'json'}), expected_out)


class TestRequestDailyData(TestCase):
    """Unit tests for request_daily_data
    """
    _daily_url = "https://api.weather.gc.ca/collections/climate-daily/items"
    _daily_queryable = "https://api.weather.gc.ca/collections/climate-daily/queryables"

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
            url = self._daily_queryable,
            match = [responses.matchers.query_param_matcher({'f':'json'}, strict_match=False)],
            json = queryable_json,
            status = 200
        )

        # For the number matched check
        responses.get(
            url = self._daily_url,
            match = [responses.matchers.query_param_matcher({'f': 'json', 'limit': 1, 'offset': 0},
                                                            strict_match=False)],
            json = {'numberMatched': number_matched},
            status = 200
        )

    @responses.activate
    def test_unqueryable_removed(self):
        """Test that unqueryable properties are ignored
        """
        self._make_initial_check_responses(['CLIMATE_IDENTIFIER', 'LOCAL_DATE'])

        responses.get(
            url = self._daily_url,
            json = {"type":"FeatureCollection",
                    "numberReturned":2,
                    "features":[{"type": "Feature",
                                 "id": "11.11.11",
                                 "geometry":{"type":"Point","coordinates": [-112.79972222222224,49.63027777777778]},
                                 "properties":{"LOCAL_DATE": "2024-03-02 00:00:00"}}]},
            status = 200
        )

        expected_out = gpd.GeoDataFrame({'id':["11.11.11"],
                                         'geometry':[Point(-112.79972222222224, 49.63027777777778)],
                                         'LOCAL_DATE':pd.Series([datetime(year=2024,month=3,day=2)],
                                                                dtype='datetime64[ms]')})

        with disable_all_logging(highest_level=logging.WARNING) as _:
            data_out = request_daily_data(station_id=2263,
                                          date_interval=datetime(year=2024,month=3,day=2),
                                          properties=['BAD_PROP', 'LOCAL_DATE'])

        pd.testing.assert_frame_equal(data_out, expected_out)


    @responses.activate
    def test_skip_when_none_matched(self):
        """Test that we skip any other requests when there are no matches
        """
        test_properties = ['LOCAL_DAY']
        self._make_initial_check_responses(properties=test_properties, number_matched=0)

        data_out = request_daily_data(station_id=123,
                                      date_interval=datetime(year=1992, month=10, day=2),
                                      properties=test_properties)
        pd.testing.assert_frame_equal(data_out, gpd.GeoDataFrame())


    @responses.activate
    def test_multi_request_manage(self):
        """Test that when multiple requests are made to the API, that the
        results are concatenated
        """
        test_properties = ['TOTAL_PRECIPITATION']
        self._make_initial_check_responses(properties=test_properties, number_matched=2)

        # have the responses spit out one row at a time
        responses.get(
            url = self._daily_url,
            json = {"type": "FeatureCollection",
                    "features":[{"type": "Feature",
                                 "id": "7.8.9.10",
                                 "geometry": {"type": "Point", "coordinates": [-112.05,49.1333333333333]},
                                 "properties": {"TOTAL_PRECIPITATION": 1.1}}]},
            status = 200
        )

        responses.get(
            url = self._daily_url,
            json = {"type": "FeatureCollection",
                    "features":[{"type": "Feature",
                                 "id": "7.8.9.10",
                                 "geometry": {"type": "Point", "coordinates": [-112.05,49.1333333333333]},
                                 "properties": {"TOTAL_PRECIPITATION": 0}
                                 }]},
            status = 200
        )

        # setting the limit to 1 should cause two requests to happen, one for each row
        data_out = request_daily_data(station_id=8804,
                                      date_interval=[datetime(year=2000, month=1, day=26),
                                                     datetime(year=2000, month=1, day=27)],
                                      properties=test_properties,
                                      limit=1)


        expected_out = gpd.GeoDataFrame({'id': ["7.8.9.10"] * 2,
                                         'geometry': [Point(-112.05, 49.1333333333333)] * 2,
                                         'TOTAL_PRECIPITATION': [1.1, 0]
                                         })

        pd.testing.assert_frame_equal(data_out, expected_out)

    @responses.activate
    def test_column_reorder(self):
        """Ensure that the columns are in the order requested
        """
        # Have the API send back the columns in mixed order
        test_properties = ['MEAN_TEMPERATURE', 'MAX_TEMPERATURE', 'MIN_TEMPERATURE']

        self._make_initial_check_responses(properties=test_properties, number_matched=2)
        responses.get(
            url = self._daily_url,
            json = {"type": "FeatureCollection",
                    "features":[{"type": "Feature",
                                 "id": "444.444",
                                 "geometry": {"type": "Point", "coordinates": [-113.5,53.32]},
                                 "properties": {"MEAN_TEMPERATURE": -4.9,
                                                "MAX_TEMPERATURE": -1.8,
                                                "MIN_TEMPERATURE": -7.9}},
                                {"type": "Feature",
                                 "id": "444.444",
                                 "geometry": {"type": "Point", "coordinates": [-113.5,53.32]},
                                 "properties": {"MEAN_TEMPERATURE": -3.0,
                                                "MAX_TEMPERATURE": 1.7,
                                                "MIN_TEMPERATURE": -7.6}}]},
            status = 200
        )

        data_out = request_daily_data(station_id=1865,
                                      date_interval=[datetime(year=2012, month=1, day=2),
                                                     datetime(year=2012, month=1, day=3)],
                                      properties=test_properties
                           )
        expected_out = gpd.GeoDataFrame({'id': ['444.444'] * 2,
                                         'geometry': [Point(-113.5, 53.32)] * 2,
                                         'MEAN_TEMPERATURE': [-4.9, -3],
                                         'MAX_TEMPERATURE': [-1.8, 1.7],
                                         'MIN_TEMPERATURE': [-7.9, -7.6]})

        pd.testing.assert_frame_equal(data_out, expected_out)

class TestRequestDailyDataIntegration(TestCase):
    """Integration testing for daily data requests

    These tests actually query the API and require integration testing
    """
    def test_quality_request(self):
        """Send what should be a quality request and see if you get back what you wants
        """
        lethbridge_id = 2263
        properties = ['LOCAL_DATE', 'MAX_TEMPERATURE', 'TOTAL_RAIN']

        # just get a few days that probably shouldn't change much
        date_interval = [datetime(year=2007, month=8, day=27), datetime(year=2007, month=8, day=29)]
        output = request_daily_data(station_id=lethbridge_id,
                                    date_interval=date_interval,
                                    properties=properties)

        expected_out = gpd.GeoDataFrame(data={'id': ['3033880.2007.8.27', '3033880.2007.8.28', '3033880.2007.8.29'],
                                              'geometry': [Point(-112.79972222222223, 49.63027777777778)] * 3,
                                              'LOCAL_DATE': ['2007-08-27', '2007-08-28', '2007-08-29'],
                                              'MAX_TEMPERATURE': [17.2, 21.5, 30.3],
                                              'TOTAL_RAIN': [2.5, 0.5, 1.0]})
        expected_out['LOCAL_DATE'] = pd.to_datetime(expected_out['LOCAL_DATE'],
                                                    format='%Y-%m-%d').astype('datetime64[ms]')

        pd.testing.assert_frame_equal(output, expected_out)

    def test_modern_up_to_current_time(self):
        """Send a time stamp that claims up to current
        """
        properties=['LOCAL_MONTH', 'LOCAL_DAY']
        date_interval = [datetime(year=2025, month=6, day=20), '..']
        lethbridge_id = 49268

        output = request_daily_data(station_id=lethbridge_id,
                                    date_interval=date_interval,
                                    properties=properties)

        self.assertTrue('LOCAL_DAY' in output.columns)
        self.assertGreater(output['LOCAL_DAY'].iloc[-1], date_interval[0].day)

if __name__ == "__main__":
    main()
