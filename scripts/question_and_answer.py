#!/usr/bin/env python3
"""This contains questions asked by Dan and the answers

Many of the questions came through email exchange
"""
from datetime import datetime
import pandas as pd

from danlab import request_climate_stations

# Here are the properties I'm going to grab from the API
# I comment out the ones I'm not interested, but you can grab those, too
WEATHER_STN_PROPERTIES = [
    'LATITUDE',
    'LONGITUDE',
    'ELEVATION',
    'FIRST_DATE',
    'LAST_DATE',
    'STATION_NAME',
    'STN_ID',
    'CLIMATE_IDENTIFIER',
    'COUNTRY',
    # 'DISPLAY_CODE',
    # 'DLY_FIRST_DATE',
    # 'DLY_LAST_DATE',
    'ENG_PROV_NAME',
    'PROV_STATE_TERR_CODE',
    'ENG_STN_OPERATOR_ACRONYM',
    'ENG_STN_OPERATOR_NAME',
    # 'FRE_PROV_NAME',
    # 'FRE_STN_OPERATOR_ACRONYM',
    # 'FRE_STN_OPERATOR_NAME',
    'HAS_HOURLY_DATA',
    'HAS_MONTHLY_SUMMARY',
    'HAS_NORMALS_DATA',
    # 'HLY_FIRST_DATE',
    # 'HLY_LAST_DATE',
    # 'MLY_FIRST_DATE',
    # 'MLY_LAST_DATE',
    # 'NORMAL_CODE',
    # 'PUBLICATION_CODE',
    'STATION_TYPE',
    'TC_IDENTIFIER',
    'TIMEZONE',
    # 'WMO_IDENTIFIER',
]

stations_df =  request_climate_stations(properties=WEATHER_STN_PROPERTIES,
                                            PROV_STATE_TERR_CODE='AB')

# Q: How many stations are in Alberta?
print(f"There are {stations_df.shape[0]} stations in Alberta")

# Q: How many stations have hourly data?
n_hourly_stations = stations_df[stations_df['HAS_HOURLY_DATA'] == 'Y'].shape[0]
print(f"There are {n_hourly_stations} stations in Alberta with hourly data")

# Q: How many stations are covered -which stations have long records?
date_check = datetime(year=1920, month=1, day=1) # does the station precede this date?
stations_df['FIRST_DATE'] = pd.to_datetime(stations_df['FIRST_DATE']) # Convert the string to a datetime object
early_stations = stations_df[stations_df['FIRST_DATE'] < date_check]
print(f"There are {early_stations.shape[0]} that occur before {date_check.year}")

hourly_early = early_stations[early_stations['HAS_HOURLY_DATA'] == 'Y']
print(f"Of those early stations {hourly_early.shape[0]} have hourly data")

print("Since there are so few stations, I can list them:\n",
      f"{hourly_early[['STATION_NAME','FIRST_DATE']].to_string(index=False)}")

# Q: What are the nearest stations to the Protected Areas?
