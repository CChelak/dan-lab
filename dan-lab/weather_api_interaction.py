#!/usr/bin/env python

"""Weather API Interaction

Interact with Canada's Weather API
"""
from typing import List # for type hints
from collections.abc import Iterable  # for type hints

from datetime import datetime
import io
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm  # for adding a progress bar

WEATHER_STN_PROPERTIES = [
    'CLIMATE_IDENTIFIER',
    'COUNTRY',
    'DISPLAY_CODE',
    'DLY_FIRST_DATE',
    'DLY_LAST_DATE',
    'ELEVATION',
    'ENG_PROV_NAME',
    'ENG_STN_OPERATOR_ACRONYM',
    'ENG_STN_OPERATOR_NAME',
    'FIRST_DATE',
    # 'FRE_PROV_NAME',
    # 'FRE_STN_OPERATOR_ACRONYM',
    # 'FRE_STN_OPERATOR_NAME',
    'HAS_HOURLY_DATA',
    'HAS_MONTHLY_SUMMARY',
    'HAS_NORMALS_DATA',
    # 'HLY_FIRST_DATE',
    # 'HLY_LAST_DATE',
    'LAST_DATE',
    'LATITUDE',
    'LONGITUDE',
    # 'MLY_FIRST_DATE',
    # 'MLY_LAST_DATE',
    'NORMAL_CODE',
    'PROV_STATE_TERR_CODE',
    'PUBLICATION_CODE',
    'STATION_NAME',
    'STATION_TYPE',
    'STN_ID',
    'TC_IDENTIFIER',
    'TIMEZONE',
    'WMO_IDENTIFIER',
]


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

def parse_date_time(date_interval: datetime | Iterable[datetime] | str) -> str:
    """Parse date and time given into a form the API can understand

    Parameters
    ----------
    date_interval : datetime  |  Iterable[datetime]  |  str
        A single date and time, an interval of start date/time and end date/time
        or a string already in a form the API understands 

    Returns
    -------
    str
        A string representing the date and time or the date/time interval in the
        form that the API understands
    """
    dt_str = ""
    if date_interval is not None:
        if isinstance(date_interval, datetime):
            dt_str = date_interval.isoformat()
        elif isinstance(date_interval, list):
            dt_str = '/'.join([d.isoformat() for d in date_interval])
        else:
            # we'll assume this is a string in the format accepted by properties
            dt_str = date_interval

    return dt_str


def get_number_matched(url: str, params: dict) -> int:
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

    n_matched = get_number_matched(request_url, request_params)

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
        return pd.concat(all_hourly_data, ignore_index=True)
    return all_hourly_data


HOURLY_DATA_PROPERITES = [
    'CLIMATE_IDENTIFIER',
    'DEW_POINT_TEMP',
    'DEW_POINT_TEMP_FLAG',
    'HUMIDEX',
    'HUMIDEX_FLAG',
    'ID',
    'LATITUDE_DECIMAL_DEGREES',
    'LOCAL_DATE',
    # 'LOCAL_DAY',
    # 'LOCAL_HOUR',
    # 'LOCAL_MONTH',
    # 'LOCAL_YEAR',
    'LONGITUDE_DECIMAL_DEGREES',
    'PRECIP_AMOUNT',
    'PRECIP_AMOUNT_FLAG',
    'PROVINCE_CODE',
    'RELATIVE_HUMIDITY',
    'RELATIVE_HUMIDITY_FLAG',
    'STATION_NAME',
    'STATION_PRESSURE',
    'STATION_PRESSURE_FLAG',
    'STN_ID',
    'TEMP',
    'TEMP_FLAG',
    'UTC_DATE',
    # 'UTC_DAY',
    # 'UTC_MONTH',
    # 'UTC_YEAR',
    'VISIBILITY',
    'VISIBILITY_FLAG',
    'WEATHER_ENG_DESC',
    'WEATHER_FRE_DESC',
    'WINDCHILL',
    'WINDCHILL_FLAG',
    'WIND_DIRECTION',
    'WIND_DIRECTION_FLAG',
    'WIND_SPEED',
    'WIND_SPEED_FLAG',
]

DATES = [datetime(year=2012, month=2, day=1), datetime.now()]
st_df =  request_climate_station_info(properties=WEATHER_STN_PROPERTIES)

hr_dat = request_hourly_data(station_id=2263,
                             properties=HOURLY_DATA_PROPERITES,
                             date_interval=DATES,
                             response_format='csv')

leth_ids={'LETHBRIDGE A': 50128, 'LETHBRIDGE A(2)': 2263}

for val in leth_ids.values():
    dat = request_hourly_data(station_id=val, properties=HOURLY_DATA_PROPERITES, sortby='+LOCAL_DATE')
    file_name = f"{dat['STATION_NAME'].iloc[0].replace(' ', '_')}_ID{val}_" \
                f"{dat['LOCAL_DATE'].iloc[0].replace(' ', '_')}" \
                f"_{dat['LOCAL_DATE'].iloc[-1].replace(' ', '_')}.csv"
    dat.replace(np.nan, '')
    dat.to_csv(file_name, index=False)
