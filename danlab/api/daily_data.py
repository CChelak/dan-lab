"""Tools for acquiring daily climate data from API 
"""
from datetime import datetime
import io
from logging import getLogger
from pathlib import Path
from typing import List # for type hints
from collections.abc import Iterable  # for type hints
import time

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm  # for adding a progr`ess bar

from danlab.date_conversions import parse_date_time
from danlab.api.queryables import check_unqueryable_properties
from danlab.api.query_match import find_number_matched
from danlab.data_clean import reorder_columns_to_match_properties

logger = getLogger(__name__)


def request_daily_data(station_id: int | Iterable[int],
                        properties: Iterable,
                        date_interval: datetime | Iterable[datetime] | str = None,
                        response_format: str = 'csv',
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
    response_format : str
        Which format you want the response to return as: supports 'json' or
        'csv'
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
    limit = 10000
    request_url = "https://api.weather.gc.ca/collections/climate-daily/items"

    if unq := check_unqueryable_properties(collection='climate-daily', properties=properties):
        logger.warning('The following properties cannot be queried %s. Will ignore.', unq)
        properties = [prop for prop in properties if prop not in unq]

    request_params = {'limit': limit,
                      'offset': 0,
                      'properties': ','.join(properties),
                      'STN_ID': station_id,
                      'f': response_format,
                      **extra_params}

    if date_interval is not None:
        request_params['datetime'] = parse_date_time(date_interval)

    n_matched = find_number_matched(request_url, request_params)

    all_daily_data = []
    n_iter = np.int64(np.ceil(n_matched / limit))
    with tqdm(total=n_iter, desc=f"Getting daily data for Station {station_id}") as pbar:
        for _ in range(n_iter):
            try:
                response = requests.get(request_url,
                                    params=request_params,
                                    timeout=100)
            except requests.ReadTimeout as e:
                logger.error("Read Timeout with error: %s\nError occurred at offset %s}", e,request_params['offset'])
                raise

            if response.status_code != 200:
                logger.error("Got invalid response at offset %s: [%s]\n%s",
                             request_params['offset'],
                             response.status_code,
                             response.text
                             )
                break

            pbar.update(1)

            if response_format == 'csv':
                daily_data = pd.read_csv(io.StringIO(response.text))
            else:
                daily_data = response.json()

            all_daily_data = pd.concat([all_daily_data, daily_data])

            request_params['offset'] += limit

    if response_format == 'csv' and len(all_daily_data) > 0:
        all_daily_data = pd.concat(all_daily_data, ignore_index=True)

        # first add columns not present in specified properties
        return reorder_columns_to_match_properties(df=all_daily_data, properties=properties)

    return all_daily_data

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
    limit = 1000
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
    n_iter = np.int64(np.ceil(n_matched / limit))
    successful_iter = 0
    with tqdm(total=n_iter, desc="Getting all daily data") as pbar:
        while successful_iter < n_iter:
            try:
                response = requests.get(request_url,
                                        params=request_params,
                                        timeout=7200)
            except requests.ReadTimeout as e:
                logger.error("Read Timeout with error: %s\nError occurred at offset %s}", e,request_params['offset'])
                raise

            print(response.request.path_url)
            if response.status_code != 200:
                logger.error("Got invalid response at offset %s: [%s] %s",
                             request_params['offset'],
                             response.status_code,
                             response.text
                             )
                logger.error("Failed on request %s", response.request.path_url)
                time.sleep(1800) # wait 30 minutes and try again
                continue

            pbar.update(1)

            daily_data = pd.read_csv(io.StringIO(response.text))

            daily_data = reorder_columns_to_match_properties(df=daily_data, properties=properties)
            all_daily_data = pd.concat([all_daily_data, daily_data], ignore_index=True)

            # Wrtie entries for a given ID to file if we received all its data, then drop from DataFrmae
            curr_ids = all_daily_data['CLIMATE_IDENTIFIER'].unique()
            for next_id in curr_ids[:-1]:
                next_id_data = all_daily_data[all_daily_data['CLIMATE_IDENTIFIER'] == next_id]

                file_name = Path(out_dir, f"{next_id_data['STATION_NAME'].iloc[0].replace(' ', '_')}_{next_id}.csv" )
                next_id_data.to_csv(file_name, index=False)

                all_daily_data = all_daily_data.drop(next_id_data.index)

            request_params['offset'] += limit
            successful_iter += 1

        if all_daily_data.empty:
            return

        for next_id in all_daily_data['CLIMATE_IDENTIFIER'].unique():
            sub_df = all_daily_data[all_daily_data['CLIMATE_IDENTIFIER'] == next_id]

            file_name = Path(out_dir, f"{sub_df['STATION_NAME'].iloc[0].replace(' ', '_')}_{next_id}.csv")
            sub_df.to_csv(file_name, index=False)
