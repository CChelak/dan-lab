"""A tool for requesting hourly data from the api

Interacts with https://api.weather.gc.ca/ to gather data
"""

from datetime import datetime

import numpy as np
import pandas as pd

from danlab import request_hourly_data

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

if __name__ == "__main__":
    hr_dat = request_hourly_data(station_id=2263,
                                 properties=HOURLY_DATA_PROPERITES,
                                 date_interval=DATES,
                                 response_format='csv')

    # Note that Lethbridge airport 2262 has no hourly data
    leth_airport_ids=[50128, 2263]

    for val in leth_airport_ids:
        dat = request_hourly_data(station_id=val, properties=HOURLY_DATA_PROPERITES, sortby='+LOCAL_DATE')

        if not isinstance(dat, pd.DataFrame):
            continue
        FILE_NAME = f"{dat['STATION_NAME'].iloc[0].replace(' ', '_')}_ID{val}_" \
                    f"{dat['LOCAL_DATE'].iloc[0].replace(' ', '_')}" \
                    f"_{dat['LOCAL_DATE'].iloc[-1].replace(' ', '_')}.csv"
        dat.to_csv(FILE_NAME, index=False)
