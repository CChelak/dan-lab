#!/usr/bin/env python3

"""Tools for requesting information on climate station info from API
"""
from collections.abc import Iterable  # for type hints
from logging import getLogger

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

from danlab.api.queryables import check_unqueryable_properties
from danlab.api.query_match import find_number_matched
from danlab.data_clean import reorder_columns_to_match_properties

logger = getLogger(__name__)

def request_climate_stations(properties: Iterable[str] | None = None,
                             **extra_params) -> gpd.GeoDataFrame:
    """Request climate station table from API

    Calls a GET reqest call to climate-stations/items and processes the response

    Parameters
    ----------
    properties : Iterable[str] | None
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-stations/items?lang=en
    extra_params :
        Extra parameters that can be accepted by API, defined in the "items"
        section in: https://api.weather.gc.ca/openapi?f=html#/climate-stations

    Returns
    -------
    gpd.GeoDataFrame
        A geo data frame with the columns of the properties requested, along
        with the geometry and id
    """
    if properties is not None and (not isinstance(properties, Iterable) or isinstance(properties, str)):
        raise ValueError("properties given must be an interable of property names")

    default_limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-stations/items"

    request_params = {'limit': default_limit,
                      **extra_params
                      }

    # Check the input properties, if they were given
    if properties is not None:
        if unq := check_unqueryable_properties(collection='climate-stations', properties=properties):
            logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
            properties = [prop for prop in properties if prop not in unq]

        request_params['properties'] = ','.join(properties)

    all_weather_stations = []
    n_matched = find_number_matched(request_url, request_params)

    if n_matched <= 0:
        logger.error("No stations found when sending a request of the following parameters %s", request_params)
        return pd.DataFrame()

    n_iter = np.int64(np.ceil(n_matched / request_params['limit']))
    response = requests.Response()
    with tqdm(total=n_iter, desc="Getting station information") as pbar:
        for _ in range(n_iter):
            try:
                # Theoretically, we can use gpd.read_file here, but the format of the parameters isn't one-to-one
                response = requests.get(request_url,
                                        params=request_params,
                                        timeout=100)
                if response.status_code != 200:
                    logger.error("An error occurred when requesting station info: [%s] %s",
                                response.status_code,
                                response.text)
                    return pd.DataFrame()
            except requests.ReadTimeout as e:
                logger.error("Read Timeout with error: %s\nError occurred at offset %s}", e,request_params['offset'])
                raise

            pbar.update(1)

            try:
                weather_stations = gpd.read_file(response.text)
                all_weather_stations.append(weather_stations)
            except pd.errors.EmptyDataError as e:
                logger.error(e)
                return pd.DataFrame()

    stations_gdf = pd.concat(all_weather_stations, ignore_index=True) # all stations as a GeoDataFrame

    return reorder_columns_to_match_properties(df=stations_gdf, properties=properties)
