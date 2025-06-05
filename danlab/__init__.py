"""A library used to research-related queries of protected areas and weather stations

In here, there is code that:

  - interacts with weather station API, such as pulling daily climate data
  - scrapes data from canadian governement databases
  - manages csv files from canada government and smartly joins them
  - checks for proximity of stations to protected areas or other stations
"""

from danlab.scrape.download_weather_data import (
    download_hourly_weather,
    download_hourly_weather_in_date_range,
)

from danlab.scrape.scrape_weather_stations import (
    gather_station_search_results,
    scrape_station_ids,
)

from danlab.date_conversions import (
    parse_date_time,
)

from danlab.api.climate_station import (
    request_climate_stations,
)

from danlab.api.hourly_data import (
    request_hourly_data,
)

from danlab.api.daily_data import (
    request_daily_data,
    write_all_daily_data_to_csv,
)

from danlab.api.queryables import (
    request_queryable_names,
    check_unqueryable_properties,
)

from danlab.api.bbox import (
    create_bbox_string,
    doctor_bbox_latlon_string,
)

from danlab.data_clean import (
    reorder_columns_to_match_properties,
)

from danlab.geospatial.proximity import (
    select_within_centroid,
    select_within_distance_of_region
)
