#!/usr/bin/env python3
"""A tool for requesting daily data from the api

Interacts with https://api.weather.gc.ca/ to gather data
"""

from datetime import datetime

from danlab.api.daily_data import request_daily_data, write_all_daily_data_to_csv
from danlab.api.climate_station_info import request_climate_station_info

DAILY_DATA_PROPERTIES = [
        "ID",
        "STATION_NAME",
        "PROVINCE_CODE",
        "LOCAL_DATE",
        "CLIMATE_IDENTIFIER",
        "LOCAL_DAY",
        "LOCAL_MONTH",
        "LOCAL_YEAR",
        "MIN_TEMPERATURE",
        "MIN_TEMPERATURE_FLAG",
        "MAX_TEMPERATURE",
        "MAX_TEMPERATURE_FLAG",
        "MEAN_TEMPERATURE",
        "MEAN_TEMPERATURE_FLAG",
        "MIN_REL_HUMIDITY",
        "MIN_REL_HUMIDITY_FLAG",
        "MAX_REL_HUMIDITY",
        "MAX_REL_HUMIDITY_FLAG",
        "TOTAL_PRECIPITATION",
        "TOTAL_PRECIPITATION_FLAG",
        "TOTAL_RAIN",
        "TOTAL_RAIN_FLAG",
        "TOTAL_SNOW",
        "TOTAL_SNOW_FLAG",
        "SNOW_ON_GROUND",
        "SNOW_ON_GROUND_FLAG",
        "COOLING_DEGREE_DAYS",
        "COOLING_DEGREE_DAYS_FLAG",
        "HEATING_DEGREE_DAYS",
        "HEATING_DEGREE_DAYS_FLAG",
        "SPEED_MAX_GUST",
        "SPEED_MAX_GUST_FLAG",
        "DIRECTION_MAX_GUST",
        "DIRECTION_MAX_GUST_FLAG",
]

DATES = [datetime(year=1820, month=1, day=1), datetime.now()]

if __name__ == "__main__":
    write_all_daily_data_to_csv(properties=DAILY_DATA_PROPERTIES,
                                date_interval=DATES,
                                out_dir = '/home/clintc/Documents/danlab/',
                                PROVINCE_CODE='AB'
                                #bbox=
                            )

#     daily_dat = request_daily_data(station_id=2263,
#                                  properties=DAILY_DATA_PROPERTIES,
#                                  date_interval=DATES,
#                                  response_format='csv',
#                                  sortby='+LOCAL_DATE')
    # daily_dat.to_csv("Lethbridge_A_2263_daily.csv")

