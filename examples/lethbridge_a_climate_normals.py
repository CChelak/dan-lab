#!/usr/bin/env python3

"""Calcuclate the normals of LETHBRIDGE_A climate station

We'll use the daily data pulled from our API and datamart, compare the results
(ensuring that they are the same).

Then we'll use our results and reform the graphs found on this webpage:
https://climate.weather.gc.ca/climate_normals/results_1981_2010_e.html?searchType=stnName&txtStationName=LETHBRIDGE+A&searchMethod=contains&txtCentralLatMin=0&txtCentralLatSec=0&txtCentralLongMin=0&txtCentralLongSec=0&stnID=2263&dispBack=1

NOTE: This method for calculating the normals is not necessary, as they have been calculated for users at the url
https://api.weather.gc.ca/collections/climate-normals

We'll follow the methodolgy laid out here:
https://collaboration.cmc.ec.gc.ca/cmc/climate/Normals/Canadian_Climate_Normals_1981_2010_Calculation_Information.pdf
"""

from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

from danlab.api.daily_data import request_daily_data

DAILY_DATA_PROPERTIES = [
        "STATION_NAME",
        "LOCAL_DATE",
        "LOCAL_MONTH",
        "LOCAL_YEAR",
        "MIN_TEMPERATURE",
        "MAX_TEMPERATURE",
        "MEAN_TEMPERATURE",
        "MIN_REL_HUMIDITY",
        "MAX_REL_HUMIDITY",
        "TOTAL_PRECIPITATION",
        "TOTAL_RAIN",
        "TOTAL_RAIN_FLAG",
        "TOTAL_SNOW",
        "TOTAL_SNOW_FLAG",
]

DAILY_DATES = [datetime(year=1981, month=1, day=1), datetime(year=2010, month=12, day=31)]

daily_data = request_daily_data(station_id=2263,
                                properties=DAILY_DATA_PROPERTIES,
                                date_interval=DAILY_DATES)

# iterate through each month, find min, max and average

summary_info = []
for month in range(1,13):
    month_data = daily_data[daily_data['LOCAL_MONTH'] == month]
    min_temp = month_data['MIN_TEMPERATURE'].mean()
    max_temp = month_data['MAX_TEMPERATURE'].mean()
    avg_temp = month_data['MEAN_TEMPERATURE'].mean()
    avg_precip = month_data['TOTAL_PRECIPITATION'].mean()
    summary_info.append([min_temp, max_temp, avg_temp, avg_precip])

summary_info = pd.DataFrame(summary_info, columns=['Min Temp', 'Max Temp', 'Avg Temp', 'Avg Precip'])
x = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax2.bar(x, summary_info["Avg Precip"], color='green', alpha=0.3)

ax1.plot(x, summary_info['Min Temp'], "-s", color='red')
ax1.plot(x, summary_info['Max Temp'], "-o", color='black')
ax1.plot(x, summary_info["Avg Temp"], "-^", color='blue')

fig.tight_layout()
plt.show()
