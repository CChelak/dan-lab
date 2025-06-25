#!/usr/bin/env python

""""Tools for converting dates for the API
"""

from collections.abc import Iterable
from datetime import datetime

def parse_date_time(date_interval: datetime | Iterable[datetime] | str) -> str:
    """Parse date and time given into a form the API can understand

    Parameters
    ----------
    date_interval : datetime  |  Iterable[datetime]  |  str
        A single date and time, an interval of start date/time and end date/time
        or a string already in a form the API understands 

    Returns
    -------
    str
        A string representing the date and time or the date/time interval in the
        form that the API understands
    """
    dt_str = ""
    if date_interval is not None:
        if isinstance(date_interval, datetime):
            dt_str = date_interval.isoformat()
        elif isinstance(date_interval, list):
            dt_str = '/'.join([d.isoformat() if isinstance(d, datetime) else d for d in date_interval])
        else:
            # we'll assume this is a string in the format accepted by properties
            dt_str = date_interval

    return dt_str
