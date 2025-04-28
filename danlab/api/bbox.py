"""Functions for altering bounding boxes with API queries

Bounding box or bbox is a set of coordinates (usually 2 pairs of longitude and
latitude) that define a region within which to request data.
"""

from typing import List

import numpy as np
from shapely import Point

def create_bbox_string(region_coord: List[Point]) -> str:
    """Convert coordinates representing Longitude/Latitude region into a string
    the API can understand

    Parameters
    ----------
    region_coord : List[Point]
        Coordinates representing the region you want to bound. Currently, this
        expects 2+ Lon/Lat points representing opposite corners of the box

    Returns
    -------
    str
        a bbox string that the API can understand, of a form:
        "<min_lon>,<min_lat>,<max_lon>,<max_lat>"

    Raises
    ------
    ValueError
        A list was not provided in region_coord
    ValueError
        At least two points were not given in region_coord
    ValueError
        The elements in the region_coord were not shapely Points
    """
    if not isinstance(region_coord, List):
        raise ValueError(f"region coord is not a list of points: type = {type(region_coord)}")
    if len(region_coord) < 2:
        raise ValueError(f"Two points needed to create bounding box : {region_coord=}")

    x = np.zeros(len(region_coord), dtype=np.float64)
    y = np.zeros(len(region_coord), dtype=np.float64)
    for ii, pt in enumerate(region_coord):
        if not isinstance(pt, Point):
            raise ValueError(f"Point {ii} given not a shapely point {type(pt)}")

        x[ii] = pt.x
        y[ii] = pt.y

    # Show the min longitude and latitude first, followed by the maximum
    return f'{x.min()},{y.min()},{x.max()},{y.max()}'

def doctor_bbox_latlon_string(bbox_in: str) -> str:
    """Make sure the longitude and latitude are in the correct order

    bbox needs to have the minimum values first, followed by max values

    NOTE: This assumes alternating longitude, latitude coordinates. If elevation
    incorporated, this will not work.

    Parameters
    ----------
    bbox_in : str
        a string with the bounding box

    Returns
    -------
    str
        the bounding box in the following format:
        "<min_lon>,<min_lat>,<max_lon>,<max_lat>"

    Raises
    ------
    ValueError
        At least 4 entries not found in a comma-separated list
    ValueError
        Entries in comma-separted list could not be converted to a float
    """
    coords = bbox_in.split(',')

    if len(coords) < 4:
        raise ValueError(f"Could not find 4 values for lat/long bbox: {coords}")

    lons = []
    lats = []

    # do a try/catch to print a more direct input-error message to the user
    try:
        lons = [float(lon) for lon in coords[0::2]] # Assuming first is always longitude
        lats = [float(lat) for lat in coords[1::2]] # Followed by latitude
    except ValueError as e:
        raise ValueError(f"Values do not appear to be a number for Latitude or Longitude: {e}") from e

    # return the number in the exact format that it came in
    lonlat_min = f"{coords[np.argmin(lons) * 2]},{coords[np.argmin(lats) * 2 + 1]}"
    lonlat_max = f"{coords[np.argmax(lons) * 2]},{coords[np.argmax(lats) * 2 + 1]}"

    return lonlat_min + ',' + lonlat_max
