#!/usr/bin/env python3

"""Tests on the query_match file in the API
"""

from unittest import TestCase, main

import responses

from danlab.util.log_util import disable_all_logging
from danlab.api.query_match import find_number_matched

class TestFindNumberMatched(TestCase):
    """Test find_number_matched
    """

    @responses.activate
    def test_bad_json(self):
        """Check that when the response cannot be converted to json, that the
        return value is 0 rather than a cryptic exception
        """
        example_url = "https://httpbin.org/get"
        responses.get(
            url = example_url,
            body = 'not-json',
            status = 200
        )

        with disable_all_logging() as _:
            self.assertEqual(find_number_matched(example_url, params={}), 0)

    @responses.activate
    def test_no_number_matched(self):
        """Ensure no failure when numberMatched is not found
        """
        example_url = "https://example.com/get"
        responses.get(
            url = example_url,
            json = {'properties': {'otherstuff':'nice'}},
            status = 200
        )

        with disable_all_logging() as _:
            self.assertEqual(find_number_matched(example_url, params={}), 0)

    @responses.activate
    def test_error_status(self):
        """Test that 0 is returned on an error message
        """
        example_url = "https://example.com/get"
        responses.get(
            url = example_url,
            json = {'error': 'parameters needed, or something'},
            status = 400
        )

        with disable_all_logging() as _:
            self.assertEqual(find_number_matched(example_url, params={}), 0)

if __name__ == "__main__":
    main()
