#!/usr/bin/env python

"""Tools for requesting information on climate station info from API
"""
from collections.abc import Iterable  # for type hints
import io
from logging import getLogger

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

from danlab.api.queryables import check_unqueryable_properties
from danlab.api.query_match import find_number_matched
from danlab.data_clean import reorder_columns_to_match_properties

logger = getLogger(__name__)

def request_climate_station_info(properties: Iterable = None,
                                 **extra_params) -> pd.DataFrame:
    """Request climate station info from API

    Calls a GET reqest call to climate-stations/items and processes the response

    Parameters
    ----------
    properties : Iterable
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-stations/items?lang=en
    extra_params :
        Extra parameters that can be accepted by API, defined in the "items"
        section in: https://api.weather.gc.ca/openapi?f=html#/climate-stations

    Returns
    -------
    pd.DataFrame
        A data frame with of requested properties and desired climate stations
   """
    limit = 10000
    properties = properties if properties is not None else []
    request_url = "https://api.weather.gc.ca/collections/climate-stations/items"

    if unq := check_unqueryable_properties(collection='climate-stations', properties=properties):
        logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
        properties = [prop for prop in properties if prop not in unq]

    request_params = {'limit': limit,
                      'properties': ','.join(properties),
                      'PROV_STATE_TERR_CODE': 'AB',
                      'f': 'csv',
                      **extra_params
                      }

    all_weather_stations = pd.DataFrame()
    n_matched = find_number_matched(request_url, request_params)

    n_iter = np.int64(np.ceil(n_matched / limit))
    with tqdm(total=n_iter, desc="Getting station information") as pbar:
        for _ in range(n_iter):
            try:
                response = requests.get(request_url,
                                        params=request_params,
                                        timeout=100)
            except requests.ReadTimeout as e:
                logger.error("Read Timeout with error: %s\nError occurred at offset %s}", e,request_params['offset'])
                raise

        if response.status_code != 200:
            logger.error("An error occurred when requesting station info: [%s] %s",
                        response.status_code,
                        response.text)
            return pd.DataFrame()

        pbar.update(1)

        weather_stations = pd.read_csv(io.StringIO(response.text))
        all_weather_stations = pd.concat([all_weather_stations, weather_stations])

    return reorder_columns_to_match_properties(df=all_weather_stations, properties=properties)
