"""Tools for joining CSVs by common traits 
"""

from logging import getLogger
from pathlib import Path, PosixPath
import re
from typing import List

import pandas as pd

logger = getLogger(__name__)

def join_station_csv_files(csv_files: List[str],
                           climate_id: str,
                           out_dir: Path,
                           basename: str,
                           encoding: str = 'ISO-8859-1') -> PosixPath | None:
    """Join a list of CSV files

    This also sorts the data by dates

    Parameters
    ----------
    csv_files : List[str]
        The CSV files to be sorted and joined
    climate_id : str
        The cliamte ID of the data coming in
    out_dir : Path
        The directory with which to place the output CSV
    basename : str
        The basename to be at the front of the output CSV file name
    encoding : str, optional
        The type of encoding to read and write the CSV files, by default 'ISO-8859-1'

    Returns
    -------
    PosixPath | None
        The path to which the file was written, or None on an error
    """
    all_csv_data = []
    for csv in csv_files:
        df = pd.read_csv(csv, encoding=encoding)
        all_csv_data.append(df)

    joined_df = pd.concat(all_csv_data)

    if joined_df.empty:
        logger.error("No information found for ID %s. Not writing CSV file.", climate_id)
        return None

    joined_df = joined_df.sort_values(by=['Date/Time'], ascending=False)

    station_name = (joined_df['Station Name'].iloc[0]).replace(' ', '_')
    start_year = joined_df['Year'].iloc[-1]
    end_year = joined_df['Year'].iloc[0]

    out_filename = out_dir / f"{basename}_{station_name}_{climate_id}_{start_year}-{end_year}.csv"
    joined_df.to_csv(out_filename, encoding=encoding, index=False)

    return out_filename.absolute()


def join_station_csv_data_by_id(in_dir: Path,
                                out_dir: Path,
                                basename: str) -> List[PosixPath]:
    """Join station CSV files by IDs found in file name

    This reads in each file into memory as a pandas DataFrame, appends rows and
    ensures all columns align between files. As a result, this is possible more
    robust, but it is quite computationally expensive.

    The data used to build this was found in the following link:
    https://dd.weather.gc.ca/climate/observations/daily/csv/AB/

    At the time of creation, it had a name formatted as follows:
    climate_daily_AB_<climate_id>_<year>_P1D.csv

    This assumes that the Climate ID is in the file name, which is defined
    as 7-character unique identifier (e.g. '303A0Q6').
    See documentation: https://climate.weather.gc.ca/doc/Technical_Documentation.pdf

    If it is known that columns align between files and are of the same format,
    it is recommended to append the files via command line (i.e. with join, awk,
    or perl).

    Parameters
    ----------
    in_dir : Path
        The directory with which to read CSVs
    out_dir : Path
        The directory with which to place output CSVs (a CSV file joining files
        with common ID)
    basename : str
        The basename of the file to use for the output file. Output will then be
        of the format <out_dir>/<basename>_<Station name>_<ID>_<start year>_<end year>.csv for each unique ID

    Returns
    -------
    List[PosixPath]
        Absolute paths of all files that were written
    """
    if not isinstance(in_dir, Path):
        logger.warning("A Path-like object is needed for in_dir, but type %s given. Attempting to coerce to Path",
                       type(in_dir))
        in_dir = Path(in_dir)

    if not isinstance(out_dir, Path):
        logger.warning("A Path-like object is needed for out_dir, but type %s given. Attempting to coerce to Path",
                       type(out_dir))
        out_dir = Path(out_dir)

    csv_list = [str(csv) for csv in in_dir.glob("*.csv")]
    csv_list.sort(reverse=True) # sort with most-recent dates first

    csv_sorted = {}
    for csv in csv_list:
        id_match = re.search(r'_(\w{7})_', csv)
        if not id_match:
            logger.error('Could not find ID in csv named "%s". Skipped.', csv)
            continue
        csv_id = id_match.group(1)

        # create key and empty list value if not already present, then append
        csv_sorted.setdefault(csv_id, []).append(csv)

    out_files = []
    for c_id, csv_list in csv_sorted.items():
        out_filename = join_station_csv_files(csv_files=csv_list, climate_id=c_id, out_dir=out_dir, basename=basename)

        if out_filename is None:
            continue

        out_files.append(out_filename)

    return out_files
