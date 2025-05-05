"""Tools for acquiring daily climate data from API 
"""
from datetime import datetime
import io
from logging import getLogger
import math
from pathlib import Path
from typing import List # for type hints
from collections.abc import Iterable  # for type hints
import time

import pandas as pd
import requests
from tqdm import tqdm  # for adding a progr`ess bar

from danlab.date_conversions import parse_date_time
from danlab.api.queryables import check_unqueryable_properties
from danlab.api.query_match import find_number_matched
from danlab.data_clean import reorder_columns_to_match_properties

logger = getLogger(__name__)

def request_data_frame(url: str, params: dict) -> pd.DataFrame | None:
    """Perform a request to the API and handle errors

    Parameters
    ----------
    url : str
        The url with which to perform the request
    params : dict
        The parameters to pass to the API GET request

    Returns
    -------
    pd.DataFrame | None
        The data frame representing the CSV gotten from request, None on failure
    """
    offset = params['offset'] if 'offset' in params else 0
    response = None

    try:
        response = requests.get(url,
                            params=params,
                            timeout=100)
    except requests.ReadTimeout as e:
        logger.error("Read Timeout with error: %s\nError occurred at offset %s}", e, offset)
        return None

    if response.status_code != 200:
        logger.error("Got invalid response at offset %s: [%s]\n%s",
                     offset,
                     response.status_code,
                     response.text
                     )
        return None

    return pd.read_csv(io.StringIO(response.text))


def request_daily_data(station_id: int | Iterable[int],
                       properties: Iterable,
                       date_interval: datetime | Iterable[datetime] | str = None,
                       **extra_params) -> pd.DataFrame | List[dict]:
    """Request daily data from API

    Calls a GET reqest call to climate-daily/items and processes the response

    Parameters
    ----------
    station_id : int | Iterable[int]
        The station ID(s) to query
    properties : Iterable
        A list of climate-station properties to gather from the API.
        Allowed properties correspond to the columns found in the link:
        https://api.weather.gc.ca/collections/climate-daily/items?lang=en
    date_interval : datetime | Iterable[datetime] | str
        If a single date given, return hourly weather data for that date

        If a list or other iterable (up to 2 elements) given, it will create
        a string representing an interval of time, in a form that API can
        understand. Note, you can give as one of the elements the string '..'
        meaning all entries up to the other time, e.g. [datetime(...), '..']
        means "from date given to now."

        If None given, date is not considered in the request
    extra_params :
        Extra parameters that can be accepted by API, defined in the "items"
        section in: https://api.weather.gc.ca/openapi?f=html#/climate-daily

    Returns
    -------
    pd.DataFrame | dict
        A data frame of the requested daily data, with properties requested as
        columns

        If request was to be made in json format, a list of dictionaries will be
        given, where each dictionary represents the json file returned in the
        response
    """
    default_limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-daily/items"

    if unq := check_unqueryable_properties(collection='climate-daily', properties=properties):
        logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
        properties = [prop for prop in properties if prop not in unq]

    request_params = {'limit': default_limit,
                      'offset': 0,
                      'properties': ','.join(properties),
                      'STN_ID': station_id,
                      'f': 'csv',
                      **extra_params}

    if date_interval is not None:
        request_params['datetime'] = parse_date_time(date_interval)

    n_matched = find_number_matched(request_url, request_params)

    all_daily_data = []
    n_iter = math.ceil(n_matched / request_params['limit'])
    with tqdm(total=n_iter, desc=f"Getting daily data for Station {station_id}") as pbar:
        successful_iter = 0
        while successful_iter < n_iter:
            daily_data = request_data_frame(request_url, request_params)

            if daily_data is None:
                time.sleep(60)
                continue

            pbar.update(1)

            all_daily_data.append(daily_data)

            request_params['offset'] += request_params['limit']
            successful_iter += 1

    if not all_daily_data:
        return pd.DataFrame()

    all_daily_data = pd.concat(all_daily_data, ignore_index=True)

    # first add columns not present in specified properties
    return reorder_columns_to_match_properties(df=all_daily_data, properties=properties)


def write_full_set_to_csv(daily_data: pd.DataFrame, out_dir: Path):
    """Write data to CSV file, if data has fully been captured

    This assumes that data is read from API sorted by of CLIMATE_IDENTIFIER.
    Therefore, if two IDs are present, then the first has been fully read.

    Files are written with the name of the following format:
    <station name>_<climate ID>.csv

    Parameters
    ----------
    daily_data : pd.DataFrame
        The daily data to write to file, if ready
    out_dir : Path
        The directory with which to write to file
    """
    # Wrtie entries for a given ID to file if we received all its data, then drop from DataFrmae
    curr_ids = daily_data['CLIMATE_IDENTIFIER'].unique()
    for next_id in curr_ids[:-1]: # loop through all but the last ID
        next_id_data = daily_data[daily_data['CLIMATE_IDENTIFIER'] == next_id]

        file_name = Path(out_dir, f"{next_id_data['STATION_NAME'].iloc[0].replace(' ', '_')}_{next_id}.csv" )
        next_id_data.to_csv(file_name, index=False)

        daily_data = daily_data.drop(next_id_data.index)

def write_all_daily_data_to_csv(properties: Iterable,
                                date_interval: datetime | Iterable[datetime] | str = None,
                                out_dir: Path = Path('.'),
                                **extra_params):
    """Write all daily data to CSVs

    Parameters
    ----------
    properties : Iterable
        Climate-daily properties to query the API
    date_interval : datetime | Iterable[datetime] | str, optional
        If a single date given, return hourly weather data for that date

        If a list or other iterable (up to 2 elements) given, it will create
        a string representing an interval of time, in a form that API can
        understand. Note, you can give as one of the elements the string '..'
        meaning all entries up to the other time, e.g. [datetime(...), '..']
        means "from date given to now."

        If None given, date is not considered in the request

    Raises
    ------
    ValueError
        Properties are missing that are required to name the files
    """
    # pylint: disable=R0914
    limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-daily/items"

    if unq := check_unqueryable_properties(collection='climate-daily', properties=properties):
        logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
        properties = [prop for prop in properties if prop not in unq]

    required_properties = ['CLIMATE_IDENTIFIER', 'STATION_NAME']
    if not all(req in properties for req in required_properties):
        raise ValueError(f"The following properties are needed to name the CSV properly: {required_properties}")

    request_params = {'limit': limit,
                      'offset': 0,
                      'properties': ','.join(properties),
                      'f': 'csv',
                      'sortby': '+CLIMATE_IDENTIFIER,+LOCAL_DATE',
                      **extra_params}

    if date_interval is not None:
        request_params['datetime'] = parse_date_time(date_interval)

    all_daily_data = pd.DataFrame()

    n_matched = find_number_matched(request_url, request_params) + request_params['offset']
    n_iter = math.ceil(n_matched / limit)
    successful_iter = 0
    with tqdm(total=n_iter, desc="Getting all daily data") as pbar:
        while successful_iter < n_iter:
            daily_data = request_data_frame(request_url, request_params)

            if daily_data is None:
                time.sleep(60)
                continue

            daily_data = reorder_columns_to_match_properties(df=daily_data, properties=properties)
            all_daily_data = pd.concat([all_daily_data, daily_data], ignore_index=True)

            write_full_set_to_csv(all_daily_data, out_dir=out_dir)

            pbar.update(1)

            request_params['offset'] += limit
            successful_iter += 1

        if all_daily_data.empty:
            return

        for next_id in all_daily_data['CLIMATE_IDENTIFIER'].unique():
            sub_df = all_daily_data[all_daily_data['CLIMATE_IDENTIFIER'] == next_id]

            file_name = Path(out_dir, f"{sub_df['STATION_NAME'].iloc[0].replace(' ', '_')}_{next_id}.csv")
            sub_df.to_csv(file_name, index=False)
    # pylint: enable=R0914
