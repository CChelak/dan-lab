#!/usr/bin/env python3

"""Test the alberta county functions and objects
"""
from collections.abc import Iterable
from unittest import TestCase, main

import responses

from danlab.api.alberta_counties import (ALBERTA_SERVICE_URL,
                                         find_alberta_county_queryables,
                                         check_alberta_unqueryable_fields)
from danlab.util.log_util import disable_all_logging

class TestFindAlbertaCountyQueryables(TestCase):
    """Unit tests for find_alberta_county_queryables function"""

    @responses.activate
    def test_empty_list_request_error(self):
        """Test that an empty list is given on a request error
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      body='ERROR',
                      status=400)

        with disable_all_logging() as _:
            queryables = find_alberta_county_queryables()
            self.assertEqual(len(queryables), 0)

    @responses.activate
    def test_no_fields_key(self):
        """Ensure things don't explode when no 'fields' key is present
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Messed Up',
                            'description': 'They changed something',
                            'geometryType': 'esriNonsense'},
                      status=200)

        with disable_all_logging() as _:
            queryables = find_alberta_county_queryables()
            self.assertEqual(len(queryables), 0)

    @responses.activate
    def test_no_name_key(self):
        """Ensure things don't explode when no 'fields' key is present
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'No names',
                            'description': 'They removed the name key',
                            'geometryType': 'esriNonsense',
                            'fields':[{'type': 'esriFieldTypeGlobalID',
                                       'alias': 'GlobalID',
                                       'length': 38,
                                       'domain': None}]},
                      status=200)

        with disable_all_logging() as _:
            queryables = find_alberta_county_queryables()
            self.assertEqual(len(queryables), 0)

    @responses.activate
    def test_valid_query(self):
        """See that I get the list of strings I expect when querying
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Only names',
                            'description': 'They gave us only names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'IDEA'},
                                      {'name': 'BACON'},
                                      {'name': 'MOON'}]},
                      status=200)

        expected_out = ['IDEA', 'BACON', 'MOON']
        queryables = find_alberta_county_queryables()

        self.assertEqual(queryables, expected_out)

class TestCheckAlbertaUnqueryableFields(TestCase):
    """Unit tests for check_alberta_unqueryable_fields function
    """
    @responses.activate
    def test_wildcard(self):
        """See if passing in a wildcard is ok, returning no bad fields
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Contrived',
                            'description': 'We only have names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'MOUNTAIN'},
                                      {'name': 'ID'},
                                      {'name': 'LLAMA'}]},
                      status=200)

        bad_options = check_alberta_unqueryable_fields(fields_in='*')
        self.assertEqual(len(bad_options), 0)

    @responses.activate
    def test_bad_string_csv_fields(self):
        """See if this can process a comma-separated string of fields
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Contrived',
                            'description': 'Some silly names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'COUNTY_NAME'},
                                      {'name': 'MONKEY'},
                                      {'name': 'LOCAL_ID'}]},
                      status=200)

        bad_options = check_alberta_unqueryable_fields(fields_in='LEMON,MONKEY,LOCAL_ID')
        self.assertEqual(bad_options, ['LEMON'])

    @responses.activate
    def test_bad_list_input(self):
        """Pass in a list and see if it returns bad fields
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Contrived',
                            'description': 'Some silly names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'COUNTY_NAME'},
                                      {'name': 'WALLET'},
                                      {'name': 'ENORMOUS_NUM'}]},
                      status=200)

        fields = ['COUNTY_NAME', 'BEANS', 'COINS', 'ENORMOUS_NUM']
        bad_options = check_alberta_unqueryable_fields(fields_in=fields)
        self.assertEqual(bad_options, ['BEANS', 'COINS'])

    @responses.activate
    def test_all_good_list(self):
        """Pass in a completely fine list of fields and see that it has empty list
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Contrived',
                            'description': 'Some silly names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'ONE'},
                                      {'name': 'TWO'},
                                      {'name': 'THREE'},
                                      {'name': 'FOUR'}]},
                      status=200)

        fields = ['THREE', 'TWO', 'FOUR']
        bad_options = check_alberta_unqueryable_fields(fields_in=fields)
        self.assertEqual(bad_options, [])

    @responses.activate
    def test_all_good_string(self):
        """Pass in completely healthy csv string and get empty list back
        """
        responses.get(url=ALBERTA_SERVICE_URL,
                      json={'id': '114',
                            'type': 'Contrived',
                            'description': 'Some silly names',
                            'geometryType': 'esriNonsense',
                            'fields':[{'name': 'HOW'},
                                      {'name': 'ARE'},
                                      {'name': 'YOU'},
                                      {'name': 'DOING'}]},
                      status=200)

        fields = 'ARE,DOING,HOW'
        bad_options = check_alberta_unqueryable_fields(fields_in=fields)
        self.assertEqual(bad_options, [])

class TestRequestAlbertaCounties(TestCase):
    """Unit tests for request_alberta_counties function
    """
    _alberta_service_url = ALBERTA_SERVICE_URL
    _alberta_query = f"{ALBERTA_SERVICE_URL}/query"

    def _make_initial_check_responses(self, fields: Iterable[str],
                                      number_matched: int = 1,
                                      max_items_per_request: int = 1000):
        """Add additional responses to the queue that check queryables and
        number matched

        Parameters
        ----------
        fields : Iterable[str]
            The queryable fields to include in the queryables response
        number_matched : int
            Number of matched items to return to user, default is 1
        max_items_per_request : int
            The maximum number of items per request
        """
        # For when queryables is checked
        queryable_json = { "fields": { field: {'name': field, 'type': 'string'} for field in fields } }

        responses.get(
            url = self._alberta_service_url,
            match = [responses.matchers.query_param_matcher({'f':'json'}, strict_match=False)],
            json = queryable_json,
            status = 200
        )

        # For the number matched check
        responses.get(
            url = self._alberta_query,
            match = [responses.matchers.query_param_matcher({'f': 'json', 'returnCountOnly': True},
                                                            strict_match=False)],
            json = {'count': number_matched},
            status = 200
        )

        # To find the step size, i.e. max number of items returned in a request
        responses.get(
            url = self._alberta_service_url,
            match = [responses.matchers.query_param_matcher({'f': 'json'},
                                                            strict_match=False)],
            json = {'maxRecordCount': max_items_per_request},
            status = 200
        )

if __name__ == "__main__":
    main()
