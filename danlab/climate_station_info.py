#!/usr/bin/env python

"""Tools for requesting information on climate station info from API
"""
from collections.abc import Iterable  # for type hints
import io

import pandas as pd
import requests

def request_climate_station_info(properties: Iterable = None,
                                 response_format: str = 'csv',
                                 **extra_params) -> pd.DataFrame | dict:
    """Request climate station info from API

    Calls a GET reqest call to climate-stations/items and processes the response

    Parameters
    ----------
    properties : Iterable
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-stations/items?lang=en
    response_format : str
        The format to retun the data
    extra_params :
        Extra parameters that can be accepted by API, defined in the "items"
        section in: https://api.weather.gc.ca/openapi?f=html#/climate-stations

    Returns
    -------
    pd.DataFrame | dict
        A data frame with the reqeusted properties of desired climate stations

        If request was to be made in json format, a dictionary representing the
        json file will be given
   """
    properties = properties if properties is not None else []
    request_params = {'limit': 10000,
                      'properties': ','.join(properties),
                      'PROV_STATE_TERR_CODE': 'AB',
                      'f': response_format,
                      **extra_params}

    response = requests.get("https://api.weather.gc.ca/collections/climate-stations/items",
                            params=request_params,
                            timeout=100)

    if response_format == 'csv':
        weather_stations = pd.read_csv(io.StringIO(response.text))
        weather_stations = weather_stations.rename(columns={'x': 'Longitude', 'y': 'Latitude'})
    elif response_format == 'json':
        weather_stations = response.json()

    return weather_stations
