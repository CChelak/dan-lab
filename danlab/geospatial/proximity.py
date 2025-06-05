"""Tools to associate points within a certain proximity of a shape or reference point

These tools are largely shortcuts for geopandas. With that, they are more
limited in their scope. For example, inputs are expected to be in longitude and
latitude. If you are finding yourself operating in other coordinate systems, or
having to convert from geopandas objects to shapely objects to use these, then
foregoing these functions and getting comfortable using with geopandas is
advised.
"""
from collections.abc import Iterable
from numbers import Real

from geopandas import GeoSeries
from shapely import Point, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry

def select_within_centroid(reference_lonlat: BaseGeometry,
                           points_in_lonlat: Iterable[Point],
                           distance: Real,
                           crs: str = "EPSG:3402") -> GeoSeries:
    """Select points that fall within a distance of a reference point

    Parameters
    ----------
    reference_lonlat : BaseGeometry
        The reference shape/point in longitude/latitude in which each point in
        will calculate distance from. If a Point was not given, reference point
        is the object's centroid
    points_in_lonlat : Iterable[Point]
        The points to check if they are within given distance of reference,
        should be in longitude/latitude
    distance : Real
        The maximum allowed distance from centroid. Units depend on the crs
        passed in
    crs : str, optional
        A Coordinate Reference System accepted by geopanadas. This is the CRS
        with which to convert all points and determine which unit the distance
        is in, default is to pick an Alberta CRS projection that operates in
        meters (EPSG:3402)

    Returns
    -------
    GeoSeries
        The values of `points_in_lonlat` that fell within the distance provided
    """
    if not isinstance(reference_lonlat, BaseGeometry):
        raise ValueError("The reference point to find centroid must be a shapely geometry")
    if not isinstance(distance, Real):
        raise ValueError("Distance given is not a real number")
    for ii, pt in enumerate(points_in_lonlat):
        if not isinstance(pt, Point):
            raise ValueError(f"Value in points_in_lonlat at {ii} is not a shapely.Point object")

    base_crs = "EPSG:4326" # global longitude and latitude (degrees)

    pts_series_lonlat = GeoSeries(points_in_lonlat, crs=base_crs)
    pts_series_crs = pts_series_lonlat.to_crs(crs=crs)

    # Convert the reference point the proper CRS
    ref_pt = GeoSeries(reference_lonlat.centroid, crs=base_crs) # start in world CRS
    ref_pt = ref_pt.to_crs(crs=crs).iloc[0] # convert to desired CRS

    return pts_series_lonlat[pts_series_crs.dwithin(other=ref_pt, distance=distance)]


def select_within_distance_of_region(region: Polygon | MultiPolygon,
                                     points: GeoSeries,
                                     distance: Real,
                                     crs: str = "EPSG:3402") -> GeoSeries:
    """Select which points given are within a distance of a region

    Parameters
    ----------
    region : Polygon | MultiPolygon
        A region, assumed to be in the same CRS as the points given
    points : GeoSeries
        Points given to find which are within given distance of region
    distance : Real
        The maximum distance with which the points can be from the region to be
        accepted. The unit of distance depends on crs given
    crs : _type_, optional
        A Coordinate Reference System accepted by geopanadas. This is the CRS
        with which to convert all points and determine which unit the distance
        is in; default is to pick an Alberta CRS projection that operates in
        meters (EPSG:3402)

    Returns
    -------
    GeoSeries
        All points that are within the distance from the region given
    """
    if not isinstance(region, (Polygon, MultiPolygon)):
        raise ValueError("The region given must be a shapely Polygon or MultiPolygon")
    if not isinstance(points, GeoSeries):
        raise ValueError("The points given must be a GeoSeries object")
    if not isinstance(distance, Real):
        raise ValueError("Distance given is not a real number")

    points_crs = points.to_crs(crs=crs)

    polygon_crs = GeoSeries(region, crs=points.crs).to_crs(crs=crs).iloc[0]

    # return the points in the same CRS as the input, selecting the ones that fall in the distance
    return points[points_crs.dwithin(polygon_crs, distance=distance)]
