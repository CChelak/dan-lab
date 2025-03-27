#!/usr/bin/env python
"""A Tool to request station information from weather API

Interacts with https://api.weather.gc.ca/ to gather data
"""

from danlab import request_climate_station_info

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

if __name__ == "__main__":
    st_df =  request_climate_station_info(properties=WEATHER_STN_PROPERTIES,
                                          PROV_STATE_TERR_CODE='AB')
