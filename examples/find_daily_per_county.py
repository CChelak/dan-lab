#!/usr/bin/env python3

"""An example of getting stations with quality data for each alberta county

In this example, I was asked to get the best stations with data going back to
1970 in each of the following counties:

  - Forty Mile
  - Warner
  - Wheatland
  - Flagstaff
  - Kneehill
  - Lethbridge
  - Wainwright
  - Cardston
  - Newell
  - Taber
  - Mountain View
  - Paintearth
  - Starland
  - Stettler
  - Willow Creek

To do this, we will:
  1. pull down all Alberta stations
  2. remove the ones without data going back to 1970
  3. pull down the county shape files
  4. loop through each county we're interested in and get stations that fall
     within them
"""

# %% Import the needed dependencies

import os
from datetime import datetime
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from adjustText import adjust_text

from danlab import (add_missing_days,
                    calc_daily_data_coverage_percentages,
                    calc_percent_rows_fully_covered,
                    request_alberta_counties,
                    request_daily_data,
                    request_climate_stations,
                    select_within_distance_of_region,
                    write_daily_data_to_csv,
                    )

ALBERTA_10TM_CRS = 3401 # Use this a coordinate reference system

#%% Grab all the climate stations in Alberta
station_properties = [
    'STATION_NAME',
    'CLIMATE_IDENTIFIER',
    'STN_ID',
    'FIRST_DATE',
    'LAST_DATE',
    'PROV_STATE_TERR_CODE',
    'STATION_TYPE',
    'HAS_HOURLY_DATA', # We can sometimes create daily data from this. If too many hourly missed, no daily in API
    ]
ab_stations = request_climate_stations(properties=station_properties, PROV_STATE_TERR_CODE='AB')

# Let's take a look at what we got
print(ab_stations)

#%% Find stations in our desired date range

# We can extract all stations that go back to 1970
old_stations = ab_stations[ab_stations['FIRST_DATE'] <= datetime(year=1970, month=1, day=1)]

# And then check how many extend to modern time.
stns_fully_in_range = old_stations[old_stations['LAST_DATE'] >= datetime(year=2024, month=12, day=31)]

# Let's see what we have left
print(stns_fully_in_range[['STATION_NAME', 'FIRST_DATE', 'LAST_DATE']])
print(f'{stns_fully_in_range.shape=}') # at the time of running, there were only 14 stations

# %% Looking at what we excluded
# Warning: some of these stations were broken up into separate IDs!
# We might have lost information. Look here at the lethbridge stations
lethbridge_stns = ab_stations[ab_stations['STATION_NAME'].str.contains('LETHBRIDGE')]
print(lethbridge_stns[['STATION_NAME', 'FIRST_DATE', 'LAST_DATE']])

# dates are all over the place, but for our purposes, we could view much of these as equivalent

lethbridge_stns_m = lethbridge_stns.to_crs(epsg=ALBERTA_10TM_CRS)
lethbridge_stn_2263_geom = lethbridge_stns_m[lethbridge_stns_m['STN_ID'] == 2263].iloc[0].geometry
lethbridge_stns_m['DIST_FROM_2263'] = lethbridge_stns_m.distance(lethbridge_stn_2263_geom)

print(lethbridge_stns_m.loc[lethbridge_stns_m['DIST_FROM_2263'] < 500,
                            ['STATION_NAME', 'STN_ID', 'FIRST_DATE', 'LAST_DATE']])
# look at the distances between them, in meters

# %% Grab the County shape files
ab_counties = request_alberta_counties(crs=ALBERTA_10TM_CRS)

# We'll reduce the list to the counties we're interested in
studied_county_names = ['Mountain View',
                        'Paintearth',
                        'Forty Mile',
                        'Newell',
                        'Flagstaff',
                        'Willow Creek',
                        'Cardston',
                        'Starland',
                        'Kneehill',
                        'Wainwright',
                        'Warner',
                        'Stettler',
                        'Lethbridge',
                        'Taber',
                        'Wheatland',
                        ]

studied_counties = ab_counties[ab_counties['MD_NAME'].str.contains('|'.join(studied_county_names))]
# %% Find stations for each county

# First, ensure that the Coordinate Reference Systems match
ab_stations_m = ab_stations.to_crs(studied_counties.crs)

# When you find out what you're doing: studied_counties.apply(func, axis=1)
studied_counties.apply(lambda x: select_within_distance_of_region(x.geometry,
                                                                  ab_stations_m.geometry,
                                                                  distance=0,
                                                                  crs=f'EPSG:{ALBERTA_10TM_CRS}'),
                       axis=1)


#%% Gathering all results

# pylint: disable=R0914
def write_stations_in_county_to_csv(county: pd.Series,
                                    stations: gpd.GeoDataFrame,
                                    save_dir):
    """Find all stations that fall in a county and write the station info and daily data to CSVs

    Parameters
    ----------
    county : gpd.GeoDataFrame
        The counties with which to find daily data for
    stations : gpd.GeoDataFrame
        All the stations to search for matches with the counties
    save_dir : _type_
        The high-level directory with which to save the contents. NOTE: a sub-
        directory will be formed that matches the county name, and within there,
        all data will be saved
    """
    # get stations within county
    county_dir = f'{save_dir}/{county['MD_NAME']}'
    os.makedirs(county_dir, exist_ok=True)
    print(f"Made county directory at {county_dir}")

    observation_columns = [
        'MAX_TEMPERATURE',
        'MEAN_TEMPERATURE',
        'MIN_TEMPERATURE',
        'TOTAL_PRECIPITATION',
    ]
    interpolated_columns = [ col + "_INTERP" for col in observation_columns ]
    props = ['LOCAL_DATE','STATION_NAME', 'CLIMATE_IDENTIFIER',] + observation_columns
    stns_within = stations[stations.dwithin(county.geometry, distance=0)].copy()
    stns_within['FIRST_DATE'] = stns_within['FIRST_DATE'].dt.strftime('%Y-%m-%d')
    stns_within['LAST_DATE'] = stns_within['LAST_DATE'].dt.strftime('%Y-%m-%d')

    daily_dataframes = {} # will store daily data with key=CLIMATE_IDENTIFIER and value pd.DataFrame
    indexes_to_drop = []
    for idx, stn in stns_within.iterrows():
        climate_id = stn['CLIMATE_IDENTIFIER']
        daily = request_daily_data(stn['STN_ID'], properties=props, sortby='+LOCAL_DATE')

        if daily.empty:
            print(f"No data found for station {stn['STATION_NAME']}, climate id {climate_id}. Skipping data set...")
            indexes_to_drop.append(idx)
            continue

        coverages = calc_daily_data_coverage_percentages(data_in=daily, columns=observation_columns)

        # update the station information with coverage
        stns_within.loc[idx, coverages.index] = coverages
        stns_within.loc[idx, 'FULL_COVERAGE'] = calc_percent_rows_fully_covered(data_in=daily,
                                                                                columns=observation_columns)

        # If full coverage is below 50%, discard that station from results
        if stns_within.loc[idx, 'FULL_COVERAGE'] < 0.5:
            print(f"Insufficient coverage ({stns_within.loc[idx, 'FULL_COVERAGE']}) for station" \
                  f" {stn['STATION_NAME']}, climate id {climate_id}. Dropping data set.")
            indexes_to_drop.append(idx)
            continue

        fill_plans = {'geometry': 'method=ffill',
                      'id': lambda x: f"{x['CLIMATE_IDENTIFIER']}.{x['LOCAL_DATE'].strftime('%Y.%m.%d')}",
                      'STATION_NAME': 'method=ffill',
                      'CLIMATE_IDENTIFIER': 'method=ffill'}
        daily = add_missing_days(data_in=daily, column_fill_plans=fill_plans)
        daily = daily.drop(columns=['index']) # add_missing_days added an index columns. We don't need it
        daily[interpolated_columns] = daily[observation_columns].interpolate(method='linear', axis=0)

        # if we made it this far, save daily data to dictionary
        daily_dataframes[climate_id] = daily

    # drop stations that failed in above loop, and drop a redundant id column
    stns_within = stns_within.drop(index=indexes_to_drop, columns=['id'])
    # write completed station information to CSV
    stns_within = stns_within.sort_values(by=['FULL_COVERAGE', 'TOTAL_PRECIPITATION_COVERAGE'],
                                          ascending=False).reset_index(drop=True)
    stns_within = stns_within.to_crs(epsg=4326)
    stns_within.to_csv(f"{county_dir}/{county['MD_NAME'].replace(' ', '_')}_stations.csv", index=False)

    # write daily station information to CSV
    for idx, stn in stns_within.iterrows():
        daily = daily_dataframes[stn['CLIMATE_IDENTIFIER']]
        station_name = daily['STATION_NAME'].iloc[0].replace(' ', '_')
        write_daily_data_to_csv(data_in=daily,
                                station_name=station_name,
                                prefix=str(idx),
                                output_directory=county_dir)
# pylint: enable=R0914

def set_station_county_column(county: pd.Series, stations: gpd.GeoDataFrame):
    """Update the ``COUNTY`` column of `stations` given with the `county` name

    Parameters
    ----------
    county : pd.Series
        The county who contains its name in ``MD_NAME``
    stations : gpd.GeoDataFrame
        The stations to add the name found in `county`, if it falls within
        `county`
    """
    stations.loc[stations.dwithin(county.geometry, distance=0), 'COUNTY'] = county['MD_NAME']

# %% Add a plotting function

def plot_stations_within_county(county: pd.Series, stations: gpd.GeoDataFrame, outdir: str):
    """Plot the stations within the given county to the output directory specified

    Parameters
    ----------
    county : pd.Series
        Information on a given county, with a geometry column
    stations : gpd.GeoDataFrame
        The stations to plot, if they fall within the county's geometry, must
        have a geometry column that is a GeoSeries
    outdir : str
        The name of the directory to output. Currently, it must be a string
        that has no trailing forward slash
    """
    plt.figure(figsize=(14,12), dpi=120)
    ax = plt.subplot(aspect='equal')
    gpd.GeoSeries(county.geometry).boundary.plot(ax=ax, color='#FFCF01')
    stns_within = stations[stations.dwithin(county.geometry, distance=0)]
    stns_within.geometry.plot(ax=ax, color='#003C77')
    ax.set_title(county['MD_NAME'])

    texts = list(stns_within.apply(lambda stn: plt.text(x=stn.geometry.x + 5,
                                                        y=stn.geometry.y + 5,
                                                        s=stn['STATION_NAME'],
                                                        fontsize=8),
                                   axis=1))
    adjust_text(texts, arrowprops={'arrowstyle': '->', 'color' : '#003C77'}, ax=ax)
    plt.savefig(f'{outdir}/{county["MD_NAME"]}/station_map_{county["MD_NAME"].replace(' ', '_')}.png')
# %% Add the relevant county to the station information, and then write station and daily information to CSVs

# Create a COUNTY column for stations and fill it with matching county data
studied_counties.apply(set_station_county_column, stations=ab_stations_m, axis=1)
studied_counties.apply(write_stations_in_county_to_csv,
                       stations=ab_stations_m,
                       save_dir='/home/clintc/projects/dan-lab/output/stations-by-county/',
                       axis=1)

# %% plot all
studied_counties.apply(plot_stations_within_county,
                       stations=ab_stations_m,
                       axis=1,
                       outdir='/home/clintc/projects/dan-lab/output/stations-by-county')
