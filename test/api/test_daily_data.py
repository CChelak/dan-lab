#!/usr/bin/env python3

"""Test the daily data functions and objects
"""
from collections.abc import Iterable
from datetime import datetime
import logging
from unittest import TestCase, main

import pandas as pd
import responses
import responses.matchers

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
    def test_csv_to_df(self):
        """Simulate a response of a csv and get the dataframe out
        """
        responses.get(
            url = self._daily_url,
            body = "a,b\n0,4\n1,5\n2,6\n3,7",
            status = 200
        )
        expected_out = pd.DataFrame({'a':[0,1,2,3], 'b':[4,5,6,7]})

        pd.testing.assert_frame_equal(request_data_frame(self._daily_url, params={'f':'csv'}), expected_out)


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
            match = [responses.matchers.query_param_matcher({'f': 'json', 'items': 1, 'offset': 0},
                                                            strict_match=False)],
            json = {'numberMatched': number_matched},
            status = 200
        )

    @responses.activate
    def test_unqueryable_removed(self):
        """Test that unqueryable properties are ignored
        """
        self._make_initial_check_responses(['CLIMATE_IDENTIFIER', 'LOCAL_DATE'])

        # For when the data is requested as csv
        responses.get(
            url = self._daily_url,
            body = 'x,y,LOCAL_DATE\n-112.79972222222224,49.63027777777778,2024-03-02 00:00:00',
            status = 200
        )

        expected_out = pd.DataFrame({'x':[-112.79972222222224],
                                     'y':[49.63027777777778],
                                     'LOCAL_DATE':['2024-03-02 00:00:00']})

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
        pd.testing.assert_frame_equal(data_out, pd.DataFrame())


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
            body = 'x,y,TOTAL_PRECIPITATION\n-112.05,49.1333333333333,1.1',
            status = 200
        )

        responses.get(
            url = self._daily_url,
            body = 'x,y,TOTAL_PRECIPITATION\n-112.05,49.1333333333333,0',
            status = 200
        )

        # setting the limit to 1 should cause two requests to happen, one for each row
        data_out = request_daily_data(station_id=8804,
                                      date_interval=[datetime(year=2000, month=1, day=26),
                                                     datetime(year=2000, month=1, day=27)],
                                      properties=test_properties,
                                      limit=1)


        expected_out = pd.DataFrame({'x': [-112.05,-112.05],
                                     'y': [49.1333333333333, 49.1333333333333],
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
            body = ('x,y,MIN_TEMPERATURE,MEAN_TEMPERATURE,MAX_TEMPERATURE\n'
                    '-113.5,53.32,-7.9,-4.9,-1.8\n'
                    '-113.5,53.32,-7.6,-3,1.7'),
            status = 200
        )

        data_out = request_daily_data(station_id=1865,
                                      date_interval=[datetime(year=2012, month=1, day=2),
                                                     datetime(year=2012, month=1, day=3)],
                                      properties=test_properties
                           )
        expected_out = pd.DataFrame({'x': [-113.5,-113.5],
                                     'y': [53.32,53.32],
                                     'MEAN_TEMPERATURE': [-4.9, -3],
                                     'MAX_TEMPERATURE': [-1.8, 1.7],
                                     'MIN_TEMPERATURE': [-7.9, -7.6]})

        pd.testing.assert_frame_equal(data_out, expected_out)

if __name__ == "__main__":
    main()
