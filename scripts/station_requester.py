#!/usr/bin/env python3
"""A Tool to request station information from weather API

Interacts with https://api.weather.gc.ca/ to gather data
"""

from argparse import ArgumentParser
import os

from danlab import request_climate_stations
from danlab.province import ProvinceCode
from danlab.api.bbox import doctor_bbox_latlon_string


WEATHER_STN_PROPERTIES = [
    'CLIMATE_IDENTIFIER',
    'FIRST_DATE',
    'LAST_DATE',
    'LATITUDE',
    'LONGITUDE',
    'HAS_HOURLY_DATA',
    'HAS_MONTHLY_SUMMARY',
    'HAS_NORMALS_DATA',
    'COUNTRY',
    'DISPLAY_CODE',
    'DLY_FIRST_DATE',
    'DLY_LAST_DATE',
    'ELEVATION',
    'ENG_PROV_NAME',
    'ENG_STN_OPERATOR_ACRONYM',
    'ENG_STN_OPERATOR_NAME',
    # 'FRE_PROV_NAME',
    # 'FRE_STN_OPERATOR_ACRONYM',
    # 'FRE_STN_OPERATOR_NAME',
    # 'HLY_FIRST_DATE',
    # 'HLY_LAST_DATE',
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

def ensure_file(file_in: str) -> str:
    """Ensure string is a file

    Parameters
    ----------
    file_in : str
        The file_in to check if it is a file

    Returns
    -------
    str
        The file name, as a normalized path, if it exists
    """
    full_path = os.path.realpath(os.path.expanduser(file_in))
    if not os.path.isdir(os.path.dirname(full_path)):
        raise NotADirectoryError(os.path.dirname(file_in))
    return full_path

if __name__ == "__main__":
    parser = ArgumentParser(prog='station_requester', description='Requests Canada climate stations')
    parser.add_argument('-p', '--properties', default=WEATHER_STN_PROPERTIES, help='Properties to request from API')
    parser.add_argument('-c', '--province', default=None, type=str, help='Province/State/Territory code')
    parser.add_argument('-o', '--output', default=None, type=ensure_file,
                        help='File name to output the station information. Prints results to console if none given.')
    parser.add_argument('-b', '--bbox', default=None, type=doctor_bbox_latlon_string,
                        help="Comma separated list of a pair of longitude,latitude coordinates of the bounding box")
    args = parser.parse_args()

    extra_params = {}

    if args.province is not None:
        extra_params['PROV_STATE_TERR_CODE'] = ProvinceCode(args.province)

    if args.bbox is not None:
        extra_params['bbox'] = args.bbox

    st_df =  request_climate_stations(properties=args.properties,
                                          **extra_params)

    if args.output is not None:
        st_df.to_csv(args.output, index=False)
    else:
        print(st_df.to_string())
