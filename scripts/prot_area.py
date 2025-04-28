#!/usr/bin/env python3
"""Practice with getting protected area information

Extracting the following protected areas:
    NA
        Red Rock Coulee
        Rumsey
        Milk River
        Hargrave Coulees (Prairie Coulees)
        Twin River Heritage Rangeland
        Onefour Heritage Rangeland
        Ribstone Creek Heritage Rangeland
    PP
        Dinosaur
        Cypress Hills
        Cold Lake
        Dry Island Buffalo Jump
        Dillberry Lake
        Kennedy Coulee
        Kinbrook Island
        Tillebrook
        Writing-on-Stone
    ER
        Rumsey
        Wainwright Dunes
    PRA
        Chin Coulee
    Unknown
    Permit No: 24-309
        Onefour Heritage Rangeland - Lost River
        Onefour Heritage Rangeland - Pinhorn
        Onefour Heritage Rangeland - Sage Creek
"""

import geopandas as gpd
from shapely import Point

from danlab.api.climate_station_info import request_climate_station_info

# The following were the regions that Dan was interested in
regions = {
        'NA': [
            "Red Rock Coulee",
            "Rumsey",
            "Milk River",
            "Hargrave Coulees (Prairie Coulees)",
            "Twin River Heritage Rangeland",
            "Onefour Heritage Rangeland",
            "Ribstone Creek Heritage Rangeland",
            ],
        'PP': [
            'Dinosaur',
            'Cypress Hills',
            'Cold Lake',
            'Dry Island Buffalo Jump',
            'Dillberry Lake',
            'Kennedy Coulee',
            'Kinbrook Island',
            'Tillebrook',
            'Writing-on-Stone',
            ],
        'ER': [
            'Rumsey',
            'Wainwright Dunes',
            ],
        'PRA': [
            'Chin Coulee',
            ],
        }

natural_areas = gpd.read_file("/home/clintc/projects/dan-lab/scripts/protected-area/prot_area_2024_jan.kml", layer='NA')

properties = ['CLIMATE_IDENTIFIER', 'STN_ID', 'LATITUDE', 'LONGITUDE',]
all_stations = request_climate_station_info(properties=properties)

climate_ids = ['3035840', '3035850', '3037520', '3035845', '3032450', '3044930']
nearby_stations = all_stations[all_stations['CLIMATE_IDENTIFIER'].isin(climate_ids)].copy()

#BBOX=-90,-180,90,180 how to bound

nearby_stations['Point_LLA'] = [Point(xy) for xy in zip(nearby_stations.x, nearby_stations.y)]
closest_station_idx = natural_areas.iloc[66]['geometry'].distance(nearby_stations['Point_LLA']).idxmin()
print(nearby_stations.loc[closest_station_idx])
