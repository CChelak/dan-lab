#!/usr/bin/env python

"""Scrape weather station information from Canada website

This uses a web scraping approach to the find weather station info, navigating
the http://climate.weather.gc.ca website and extracting relevant information
"""
from datetime import datetime
import re
from typing import List

from bs4 import BeautifulSoup
import pandas as pd
import requests

def gather_station_search_results(province: str,
                                  start_year: str,
                                  max_pages: int,
                                  end_date: datetime = None) -> List[BeautifulSoup]:
    """Gather all the HTML contents when searching for stations by province

    Parameters
    ----------
    province : str
        the province ID, in its two-letter abbreviation
    start_year : str
        the year to start the search
    max_pages : int
        maximum number of pages to search. Note: there are 100 entries per page
    end_date : datetime, optional
        The end date to stop searching, looks at year, month and day; by default use the current time

    Returns
    -------
    list of BeautifulSoup frames
        contains each page in the search for station IDs
    """
    end_date = end_date if end_date is not None else datetime.now()

    if not isinstance(end_date, datetime):
        raise TypeError("End date must be a datetime object")

    # Store each page in a list and parse them later
    soup_frames = []
    row_per_page = 100

    base_url = "http://climate.weather.gc.ca/historical_data/search_historic_data_stations_e.html?"
    query_province = f"searchType=stnProv&timeframe=1&lstProvince={province}&optLimit=yearRange&"
    query_year = f"StartYear={start_year}&EndYear={end_date:%Y}&Year={end_date:%Y}&Month={end_date:%m}&Day={end_date:%d}&selRowPerPage={row_per_page}&txtCentralLatMin=0&txtCentralLatSec=0&txtCentralLongMin=0&txtCentralLongSec=0&"

    for start_row in range(1, max_pages * row_per_page, row_per_page):
        print(f'Downloading rows {start_row} to {start_row + row_per_page}...')
        query_start_row = f"startRow={start_row}"

        response = requests.get(base_url + query_province + query_year + query_start_row) # Using requests to read the HTML source

        soup = BeautifulSoup(response.text, 'html.parser') # Parse with Beautiful Soup
        soup_frames.append(soup)

    return soup_frames

def scrape_station_ids(province:str, start_year: str, max_pages: int, end_date: datetime = None) -> pd.DataFrame:
    """Scrape all station IDs from website

    Parameters
    ----------
    province : str
        The two-letter province code
    start_year : str
        the start year as a 4-digit string
    max_pages : int
        maximum number of pages to search. Note: there are 100 entries per page
    end_date : datetime, optional
        The end date to stop searching, looks at year, month and day; by default use the current time

    Returns
    -------
    pd.DataFrame
        The data frame containing all the station ID information
        
    """
    province = province.capitalize()
    station_data = []
    soup_frames = gather_station_search_results(province, start_year, max_pages, end_date)

    for soup in soup_frames: # For each soup
        # Find forms of stnRequest## (e.g. 'stnRequest12') but exclude forms of name stnRequest##-sm
        forms = soup.find_all("form", {"id" : re.compile(r'stnRequest\d+$')})
        for form in forms:
            try:
                # The stationID is a child of the form
                station = form.find("input", {"name" : "StationID"})['value']

                # The station name is a sibling of the input element named lstProvince
                name = form.find("input", {"name" : "lstProvince"}).find_next_siblings("div")[0].text

                # The intervals are listed as children in a 'select' tag named timeframe
                timeframes = form.find("select", {"name" : "timeframe"}).find_all()
                intervals =[t.text for t in timeframes]

                # We can find the min and max year of this station using the first and last child
                years = form.find("select", {"name" : "Year"}).find_all()
                min_year = years[0].text
                max_year = years[-1].text

                # Store the data in an array
                data = [station, name, intervals, min_year, max_year]
                station_data.append(data)
            except IndexError as ex:
                print(ex)
            except:
                pass

    # Create a pandas dataframe using the collected data and give it the appropriate column names
    return pd.DataFrame(station_data, columns=['StationID', 'Name', 'Intervals', 'Year Start', 'Year End'])
