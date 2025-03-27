"""Tools for acquiring hourly climate data from API 
"""
from datetime import datetime
import io
from typing import List # for type hints
from collections.abc import Iterable  # for type hints

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm  # for adding a progr`ess bar

from danlab.date_conversions import parse_date_time

def find_number_matched(url: str, params: dict) -> int:
    """Get number of entries that match the request stated

    Parameters
    ----------
    url : str
        A URL to which to make the API GET request
    params : dict
        The parameters to pass with the GET request

    Returns
    -------
    int
        Number of matches of the GET request
    """
    alt_params = params.copy()
    alt_params['f'] = 'json'
    alt_params['items'] = 1

    response = requests.get(url,
                            params=alt_params,
                            timeout=100)
    if response.status_code != 200:
        print("An error occurred when querying number of entries:", response.status_code, response.text)
        return 0

    return response.json()['numberMatched']


def request_hourly_data(station_id: int | Iterable[int],
                        properties: Iterable,
                        date_interval: datetime | Iterable[datetime] | str = None,
                        response_format: str = 'csv',
                        **extra_params) -> pd.DataFrame | List[dict]:
    """Request hourly data from API

    Calls a GET reqest call to climate-hourly/items and processes the response

    Parameters
    ----------
    station_id : int | Iterable[int]
        The station ID(s) to query
    properties : Iterable
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-hourly/items?lang=en
    date_interval : datetime | Iterable[datetime] | str
        If a single date given, return hourly weather data for that date

        If a list or other iterable (up to 2 elements) given, it will create
        a string representing an interval of time, in a form that API can
        understand. Note, you can give as one of the elements the string '..'
        meaning all entries up to the other time, e.g. [datetime(...), '..']
        means "from date given to now."

        If None given, date is not considered in the request
    response_format : str
        Which format you want the response to return as: supports 'json' or
        'csv'
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
    limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-hourly/items"

    request_params = {'limit': limit,
                      'offset': 0,
                      'properties': ','.join(properties),
                      'STN_ID': station_id,
                      'f': response_format,
                      **extra_params}

    if date_interval is not None:
        request_params['datetime'] = parse_date_time(date_interval)

    n_matched = find_number_matched(request_url, request_params)

    all_hourly_data = []
    n_iter = np.int64(np.ceil(n_matched / limit))
    with tqdm(total=n_iter, desc=f"Getting hourly data for Station {station_id}") as pbar:
        for _ in range(n_iter):
            response = requests.get(request_url,
                                    params=request_params,
                                    timeout=100)

            if response.status_code != 200:
                print("Got invalid response:", response.status_code, response.text)
                break

            pbar.update(1)

            if response_format == 'csv':
                hourly_data = pd.read_csv(io.StringIO(response.text))
            else:
                hourly_data = response.json()

            all_hourly_data.append(hourly_data)

            request_params['offset'] += limit

    if response_format == 'csv' and len(all_hourly_data) > 0:
        all_hourly_data = pd.concat(all_hourly_data, ignore_index=True)
        # TODO: Find what columns are lost with this reindex
        return all_hourly_data.reindex(columns=properties)
    return all_hourly_data
