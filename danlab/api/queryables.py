#!/usr/bin/env python3
"""Tools for looking at queryable items
"""

from collections.abc import Iterable
from logging import getLogger
from typing import List

import requests

logger = getLogger(__name__)

def request_queryable_names(collection: str) -> List[str]:
    """Request the names of queryable items for a collection

    Parameters
    ----------
    collection : str
        The collection to perform a "queryables" request: i.e. .collections/<collection>/queryables

    Returns
    -------
    List[str]
        A list of queryables that can be made on the collection
    """
    request_url = "https://api.weather.gc.ca/collections/" + collection + "/queryables"

    request_params = {'f': 'json'}
    response = requests.get(request_url, params=request_params, timeout=100)

    if response.status_code != 200:
        logger.error("Got invalid response: [%s]\n%s", response.status_code, response.text)
        return []

    return [prop['title'] for prop in response.json()['properties'].values() if 'title' in prop]


def check_unqueryable_properties(collection: str, properties: Iterable) -> List[str]:
    """Check if properites given are unqueryable

    Performs an API request to find queryables, then returns any unqueryable
    properties given

    Parameters
    ----------
    collection : str
        The API collection that contains a "queryable" request
    properties : Iterable
        The properties to check if queryable

    Returns
    -------
    List[str]
        The list of properties that are not queryable
    """
    allowed_queries = request_queryable_names(collection=collection)

    return [p for p in properties if p not in allowed_queries]
