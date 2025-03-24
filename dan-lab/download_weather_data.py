#!/usr/bin/env python

"""Tools for manually downloading weather data from site

This uses a web scraping approach to the download, navigating the
http://climate.weather.gc.ca website and manually downloading csvs
"""

from datetime import datetime
from urllib.error import URLError

from dateutil.rrule import rrule, MONTHLY
import pandas as pd

def download_hourly_weather_data(stationID: int, date: datetime) -> pd.DataFrame:
    """Download hourly weather data from weather.gc.ca

    Parameters
    ----------
    stationID : int
        ID of station to be downloaded
    date : datetime
        The date with which to make the request for hourly data
    Returns
    -------
    pd.DataFrame
        A data frame containing all the hourly data for the station ID and
        timestamp given

    Raises
    ------
    URLError
        issue if unable to connect to the download point
    """

    base_url = "http://climate.weather.gc.ca/climate_data/bulk_data_e.html?"
    query_url = f"format=csv&stationID={stationID}&Year={date:%Y}&Month={date:%m}&timeframe=1"
    
    # if the date given explicitly lists the time zone information, use it
    timezone_url = f"&time={date:%Z}" if date.tzinfo is not None else ""
    api_endpoint = base_url + query_url + timezone_url

    print(api_endpoint)

    df = None
    tries = 0

    # try to read the CSV from the cite multiple times
    while df is None and tries < 30:
        try:
            df = pd.read_csv(api_endpoint, header=0)
        except URLError:
            pass
        tries += 1

    if df is None:
        raise URLError(f"Unable to get data from {api_endpoint}")

    return df

def download_hourly_weather_in_date_range(station_id: int,
                                          start_date: datetime,
                                          end_date: datetime = None) -> pd.DataFrame:
    """Download hourly between a date range

    Parameters
    ----------
    station_id : int
        The station ID with which to download the data
    start_date : datetime
        The date to begin the weather data download
    end_date : datetime, optional
        The date to end the weather data download, by default use the current time

    Returns
    -------
    pd.DataFrame
        A data frame containing all the downloaded data

    Raises
    ------
    ValueError
        If start date given is not a datetime object
    ValueError
        If end date given is not a datetime object
    """

    end_date = end_date if end_date is not None else datetime.now(tz=start_date.tzinfo)

    if not isinstance(start_date, datetime):
        raise ValueError("start_date must be datetime object")

    if not isinstance(end_date, datetime):
        raise ValueError("end_date must be datetime object")

    frames = []
    for dt in rrule(MONTHLY, dtstart=start_date, until=end_date):
        df = download_hourly_weather_data(station_id, dt)
        frames.append(df)

    weather_data = pd.concat(frames, ignore_index=True)
    weather_data.dropna(axis=1, how='all') # clear empty columns from the dataset

    return weather_data
