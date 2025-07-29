"""Tools for writing daily data to CSV
"""

from pathlib import Path

import pandas as pd

def write_daily_data_to_csv(data_in: pd.DataFrame,
                            station_name: str | pd.Index,
                            *,
                            prefix: str = "",
                            output_directory: Path | str = None,
                            **to_csv_kwargs):
    """Write the daily data to csv file with a appropriately descriptive file naem

    The file comes out of the following format, a format that I decided described
    the contents sufficiently for daily data:

        <output_dir>/<prefix>_<station_name>_<ids>_<first_date>_<last_date>.csv

    Parameters
    ----------
    data_in : pd.DataFrame
        The data the user wishes to write to a csv file, must have a
        'LOCAL_DATE' AND a 'CLIMATE_IDENTIFIER' column
    station_name : str | pd.Index
        The name of the station, if given as a string, or where the station name
        can be found, if given as an index. Will look at the first value of
        the index, if it has one. An IndexError would be raised if Index is
        empty
    prefix : str, optional
        Text to prepend to the generated file name, by default is to give no
        prefix
    output_directory : Path | str, optional
        Which directory on the system to save the file, by default, use the
        current working directory

    Raises
    ------
    TypeError
        `data_in` was not a pandas DataFrame
    TypeError
        Station name was not a string of the station name or an Index pointing
        to where in `data_in` the name was
    ValueError
        The index pointing of `station_name` was not found in `data_in`
    TypeError
        The file name `prefix` was not a string
    TypeError
        The `output_directory` was neither a path or a string
    ValueError
        The `output_directory` was not a valid path
    """
    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"Data given must be a pandas DataFrame. Type given: {type(output_directory)}")
    if not isinstance(station_name, (str, pd.Index)):
        raise TypeError(f"Station name is not a string or pandas Index. Type given: {type(station_name)}")
    if isinstance(station_name, pd.Index) and station_name[0] in data_in:
        raise ValueError(f"The index pointing to station name {station_name} was not found in data_in")
    if not isinstance(prefix, str):
        raise TypeError(f"The file name prefix is not a string. Type given: {type(prefix)}")

    if output_directory is None:
        output_directory = Path('.')
    elif isinstance(output_directory, str):
        output_directory = Path(output_directory)
    elif not isinstance(output_directory, Path):
        raise TypeError(f"Output directory must be type Path or string. Type given: {type(output_directory)}")

    if not output_directory.is_dir():
        raise ValueError(f"Output directory must be a directory. Path given: {output_directory}")

    # if station_name was pointing to where station name was, then pull out the station name there
    if isinstance(station_name, pd.Index):
        station_name = data_in[station_name].iloc[0].replace(' ', '_')

    ids_str = '_'.join(data_in['CLIMATE_IDENTIFIER'].unique().astype(str))

    # grab the dates to add to filename
    dates_as_str = data_in['LOCAL_DATE'].dt.strftime('%Y-%m-%d')
    first_date = dates_as_str.min()
    last_date = dates_as_str.max()

    # create the filename from all the fields
    filename = f'{station_name}_{ids_str}_{first_date}_{last_date}.csv'
    if prefix:
        filename = prefix + '_' + filename

    data_in.to_csv(output_directory / filename, index=False, **to_csv_kwargs)
