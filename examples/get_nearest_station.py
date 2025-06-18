#!/usr/bin/env python3

"""An example of getting the station nearest to a given cite

In this example, we will do the following:
  1. Download a KML of the protected areas
  2. Select a protected area we are concerned with
  3. Find its min/max lat/lon
  4. Find all stations within a given buffer of the lat/lon found in step (3)
  5. Download the data of each of the stations
  6. Pick the stations that are within a distance of the protected area
"""
import zipfile

import io
import requests

import geopandas as gpd
from shapely import Point

from danlab import (create_bbox_string,
                    request_climate_stations,
                    select_within_distance_of_region,
                    request_queryable_names)

# I use pylint to check the file. I'm ignoring warnings for example scripts here
# pylint: disable=C0103

# 1. We'll download alberta protected area data from their website.
response = requests.get("https://www.albertaparks.ca/media/6492787/protected-area-kmz-outline.zip", timeout=100)
with zipfile.ZipFile(io.BytesIO(response.content)) as zipped:

    # we can print the content of the downloaded zip file here
    print(zipped.filelist)

    # From the zip file, two kml files were seen. We want the one not ending in "_labels"
    # There are multiple layers to choose from. I'm picking 'NA' or 'Natural Areas'
    with zipped.open('Protected Area KMZ Outline 2024 January.kml') as fz_prot_area:
        prot_area = gpd.read_file(fz_prot_area, layer='NA')

# 2. Let's print all the natural areas and see what we are working with
print(prot_area['Name'].to_string())

# For this, we'll look at Milk River's geometry
milk_river_geo = prot_area[prot_area['Name'] == 'Milk River Natural Area'].geometry.iloc[0]

# 3. We can get the bounds of this region to build our bounding box for the stations
milk_river_bounds = milk_river_geo.bounds

# 4. Expand the bounds by a few tenths of a degree and create a bbox to pass into the station-finding API
station_bounds = [Point(milk_river_bounds[0] - 0.3, milk_river_bounds[1] - 0.3),
                  Point(milk_river_bounds[2] + 0.3, milk_river_bounds[3] + 0.3)]
station_bounds = create_bbox_string(station_bounds)

# 5. Now we'll find all stations nearby the Milk River Natural Area with an api call
# We select which properties we are interested. We can first see what's queryable
print(request_queryable_names('climate-stations'))

# Now, we select the properties we want
station_properties = ['CLIMATE_IDENTIFIER',
                      'STN_ID',
                      'LATITUDE',
                      'LONGITUDE',
                      'ELEVATION',
                      'STATION_NAME',
                      'STATION_TYPE']

# We request stations from the API with the bounding box we created
milk_river_stations = request_climate_stations(properties=station_properties, bbox=station_bounds)
milk_river_stations.to_crs(prot_area.crs)

# To project lon/lat to meters, we pick a Coordinate Reference System in Alberta
ALBERTA_10TM_CRS = "EPSG:3402"

# Select points within 100 meters of the region
nearest_stations = select_within_distance_of_region(region=milk_river_geo,
                                                    points=milk_river_stations.geometry,
                                                    distance=200,
                                                    crs=ALBERTA_10TM_CRS)
