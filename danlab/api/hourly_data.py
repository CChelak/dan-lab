"""Tools for acquiring hourly climate data from API 
"""
from datetime import datetime
from logging import getLogger
from typing import List # for type hints
from collections.abc import Iterable  # for type hints

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm  # for adding a progr`ess bar

from danlab.date_conversions import parse_date_time, is_convertible_to_date_str
from danlab.api.query_match import find_number_matched
from danlab.api.queryables import check_unqueryable_properties
from danlab.data_clean import reorder_columns_to_match_properties

logger = getLogger(__name__)

def request_hourly_data(station_id: int,
                        properties: Iterable[str],
                        date_interval: datetime | str | Iterable[datetime | str] = None,
                        **extra_params) -> pd.DataFrame | List[dict]:
    """Request hourly data from API

    Calls a GET reqest call to climate-hourly/items and processes the response

    Parameters
    ----------
    station_id : int
        The station ID to query
    properties : Iterable[str]
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-hourly/queryables?f=html
    date_interval : datetime | str | Iterable[datetime | str]
        If a single date given, return hourly weather data for that date

        If a list or other iterable (up to 2 elements) given, it will create
        a string representing an interval of time, in a form that API can
        understand. Note, you can give as one of the elements the string '..'
        meaning all entries up to the other time, e.g. [datetime(...), '..']
        means "from date given to now."

        If None given, date is not considered in the request
    extra_params :
        Extra parameters that can be accepted by API, defined in the "items"
        section in: https://api.weather.gc.ca/openapi?f=html#/climate-hourly

    Returns
    -------
    pd.DataFrame | dict
        A data frame of the requested hourly data, with properties requested as
        columns

        If request was to be made in json format, a list of dictionaries will be
        given, where each dictionary represents the json file returned in the
        response
    """
    if not isinstance(station_id, int):
        raise TypeError(f"station_id must be an int; {type(station_id)=}")
    if not isinstance(properties, Iterable):
        raise TypeError(f"Properties given must be an Iterable object of strings; {type(properties)=}")
    if not is_convertible_to_date_str(date_interval) and date_interval is not None:
        raise TypeError(f"date_interval must be datetime, str or iterable of datetime and str; {type(date_interval)=}")

    default_limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-hourly/items"

    if unq := check_unqueryable_properties(collection='climate-hourly', properties=properties):
        logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
        properties = [prop for prop in properties if prop not in unq]

    request_params = {'limit': default_limit,
                      'offset': 0,
                      'properties': ','.join(properties),
                      'STN_ID': station_id,
                      **extra_params}

    if date_interval is not None:
        request_params['datetime'] = parse_date_time(date_interval)

    n_matched = find_number_matched(request_url, request_params)

    if n_matched <= 0:
        logger.error("No daily data found when sending a request of the following parameters %s", request_params)
        return gpd.GeoDataFrame()

    all_hourly_data = []
    n_iter = np.int64(np.ceil(n_matched / request_params['limit']))
    with tqdm(total=n_iter, desc=f"Getting hourly data for Station {station_id}") as pbar:
        for _ in range(n_iter):
            response = requests.get(request_url,
                                    params=request_params,
                                    timeout=100)

            if response.status_code != 200:
                logger.error("Got invalid response at offset %s: [%s]\n%s",
                             request_params['offset'],
                             response.status_code,
                             response.text
                             )
                break

            pbar.update(1)

            hourly_data = gpd.read_file(response.text)

            all_hourly_data.append(hourly_data)

            request_params['offset'] += request_params['limit']

    all_hourly_data = pd.concat(all_hourly_data, ignore_index=True)

    return reorder_columns_to_match_properties(df=all_hourly_data, properties=properties)
