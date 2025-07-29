#!/usr/bin/env python3

"""Tools to get the Alberta Municipal Districts or counties from their API
"""
from collections.abc import Iterable
from typing import List
import urllib

from logging import getLogger
import requests

import geopandas as gpd

logger = getLogger(__name__)

ALBERTA_SERVICE_URL = ("https://geospatial.alberta.ca/titan/rest/services/boundary/"
                       "urban_and_rural_municipality/MapServer/114")

def find_alberta_county_queryables() -> List[str]:
    """Find the queryables Alberta municipal districts and counties 

    Returns
    -------
    List[str]
        A list of the field names you can query from the Alberta API
    """
    params = {'f': 'json'}
    response = requests.get(ALBERTA_SERVICE_URL, params, timeout=1000)

    if response.status_code != 200:
        logger.error("Got invalid response: [%s]\n%s", response.status_code, response.text)
        return []

    if 'fields' not in response.json():
        logger.error("Response did not contain 'fields' property")
        return []

    return [prop['name'] for prop in response.json()['fields'] if 'name' in prop]

def check_alberta_unqueryable_fields(fields_in: Iterable[str] | str) -> List[str]:
    """Check if some of the input fields given are not queryable

    Parameters
    ----------
    fields_in : Iterable[str] | str
        List of fields the user wishes to query; If string given, must be '*' or
        comma-separated list

    Returns
    -------
    List[str]
        A list of all fields not permitted by the API
    """
    # Assume if asking for all fields to ignore check
    if fields_in == '*':
        return []

    # if a string, separate by comma
    if isinstance(fields_in, str):
        fields_in = fields_in.split(',')

    allowed_fields = find_alberta_county_queryables()

    return [f for f in fields_in if f not in allowed_fields]


def request_alberta_counties(where:str = '1=1',
                      fields: Iterable[str] | str = '*',
                      crs:int = 4326) -> gpd.GeoDataFrame:
    """Query the map service at the URL given, concurrently

    Parameters
    ----------
    where : str
        where statement stating that we only want entries for which this clause
        is true; default is to include everything
    fields : Iterable[str] | str
        The fields we want pulled from the API and included in the dataframe; 
        Can be an iterable of field names or ;
        default is to include all fields
    crs : int
        The Coordinate Reference System with which to extract the data; default
        is to use WGS 84 (lon/lat)

    Returns
    -------
    gpd.GeoDataFrame
        A geo data frame containing all the entries from the query

    """
    # Define the query endpoint
    query_url = f"{ALBERTA_SERVICE_URL}/query"

    if unq := check_alberta_unqueryable_fields(fields_in=fields):
        logger.warning('The following fields cannot be queried %s. Will ignore.', unq)
        fields = [f for f in fields if f not in unq]

    # Determine the total number of records for the given where clause
    count_params = {
        "where": where,
        "returnCountOnly": True,
        "f": "json"
    }
    tot_records_json = requests.get(query_url, params=count_params, timeout=1000).json()
    tot_records = tot_records_json["count"]

    # Determine the step size for pages
    step_json = requests.get(ALBERTA_SERVICE_URL, params={'f': 'json'}, timeout=1000).json()
    step = step_json["maxRecordCount"]

    # Define query parameters
    query_params = {
        "where": where,
        "outFields": ', '.join(fields) if isinstance(fields, list) else fields,
        "outSr": crs,
        "f": "geojson",
        "orderByFields": "OBJECTID",
        "returnGeometry": True,
        "resultRecordCount": step
    }

    gdfs = []
    for offset in range(0, tot_records, step):
        # Create each offset query
        query_params['resultOffset'] = offset
        offset_query = urllib.parse.urlencode(query_params)

        gdfs.append(gpd.read_file(f"{query_url}?{offset_query}"))

    # Concatenate the resulting dataframes
    gdf = gpd.pd.concat(gdfs, ignore_index=True)

    return gdf
