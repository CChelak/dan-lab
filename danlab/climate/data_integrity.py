"""Data integrity checks and alterations for climate data
"""
from collections.abc import Iterable
from logging import getLogger

import numpy as np
import pandas as pd

logger = getLogger(__name__)

def _check_valid_fill_plans(data_in: pd.DataFrame, column_fill_plans: dict):
    if column_fill_plans is None:
        return
    if not isinstance(column_fill_plans, dict):
        raise TypeError("Column fill plan must be a dictionary, where keys are column names of data_in." \
                        f" Type given: {type(column_fill_plans)}")
    if bad_cols := set(column_fill_plans.keys()).difference(set(data_in.columns)):
        raise ValueError(f"In column_fill_plans, keys {bad_cols} are not found in data_in." +
                         f" Columns available: {list(data_in.columns)}")

# move to daily_doctor.py
def add_missing_days(data_in: pd.DataFrame,
                     date_column_name: str = 'LOCAL_DATE',
                     column_fill_plans: dict = None,) -> pd.DataFrame:
    """Add blank rows for days missing in data_in

    NOTE: As a result of adding missing dates, the resulting DataFrame will:

      - have the dates as its indices,
      - be sorted by date.
      - have the newly added dates auto-filled in the date column
      - have a new column for the old index
      - coerce the columns to new datatypes that support NaN if dates added

    Parameters
    ----------
    data_in : pd.DataFrame
        The data to adjust and fill missing dates
    date_column_name : str, optional
        The column name to find the dates in data_in, by default 'LOCAL_DATE'
    column_fill_plans : dict, optional
        Dictionary with plans to fill in data for newly created rows. A
        dictionary is given where the key is a column name found in data_in and
        the value is either a single value of the dtype that matches the column,
        a function that can be used with pd.Series.apply, or a string of the
        format "method=<method-type>", where <method-type> is a value supported
        by the "method" parameter of pd.DataFrame.fillna (e.g. 'backfill').

    Returns
    -------
    pd.DataFrame
        The original data_in, with indices now being dates, and with new rows of
        previously missing dates

    Raises
    ------
    TypeError
        data_in was not a pandas DataFrame
    TypeError
        date column name was not a string
    ValueError
        date column name was not found in data frame
    TypeError
        date column was not a datetime dtype
    """
    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"The given data is is not a pandas DataFrame. Type given: {type(data_in)}")
    if not isinstance(date_column_name, str):
        raise TypeError(f"The date column name is not a string. Type given: {type(date_column_name)=}")
    if date_column_name not in data_in.columns:
        raise ValueError(f"{date_column_name=} not found in data_in. Columns available: {list(data_in.columns)}")
    if not np.issubdtype(data_in[date_column_name], np.datetime64):
        raise TypeError(f"Date column in data_in is not a datetime dtype. {type(data_in[date_column_name])=}")

    _check_valid_fill_plans(data_in, column_fill_plans)

    first_day = data_in[date_column_name].min()
    last_day = data_in[date_column_name].max()

    # set the date column to the index and sort. The old indexes are kept as new columns
    data_out = data_in.reset_index().set_index(date_column_name, drop=False).sort_index(ascending=True).copy()

    data_out = data_out.reindex(pd.date_range(start=first_day, end=last_day, freq='D'))

    # update the date column to include the new dates
    data_out[date_column_name] = data_out.index

    # The only new columns should be the old indexes data_in, whose rows should be empty on the newly added days
    newly_added_days = data_out[data_out.columns.difference(data_in.columns)].isna().all(axis=1)
    return fill_data_frame_by_plans(data_in=data_out,
                                    column_fill_plans=column_fill_plans,
                                    rows_to_edit=newly_added_days)

def calc_daily_data_coverage_percentages(data_in: pd.DataFrame,
                                         columns: str | Iterable[str],
                                         date_column_name: str = 'LOCAL_DATE') -> float | pd.Series:
    """Calculate columns' percentage of days that contain data in the date range

    For example, say data was given with 5 days-worth of data, and we were
    checking column 'x', where 1 row in x has no data, this would return 0.8, or
    80% data coverage for column x

    NOTE: this checks coverage in the date range given in data_in. If rows were
    missing for certain days, those too would penalize coverage score

    Parameters
    ----------
    data_in : pd.DataFrame
        The data to check percent coverage in some of its columns
    columns : str | Iterable[str]
        Column names to check coverage. If multiple names given, each percentage
        will be returned separately
    date_column_name : str
        Name of the date column found in data_in

    Returns
    -------
    float | pd.Series
        If one column was given as a string, return the daily percent coverage
        of that column. If multiple columns given, a series will return with the
        index as the evaluated column names with "_COVERAGE" appended and the
        values being the daily percent coverage

    Raises
    ------
    TypeError
        data_in is not a DataFrame
    TypeError
        columns is not a string or iterable string
    ValueError
        The date column of the name date_column_name was not found in data_in
    TypeError
        The date column in data_in is not of a datetime dtype
    ValueError
        Columns given are not found int data_in
    """
    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"data_in was not a pandas DataFrame. Type given: {type(data_in)=}")
    if not isinstance(columns, (str, Iterable)):
        raise TypeError(f"columns given must be a string or iterable of strings. Type given: {type(columns)=}")
    if not isinstance(date_column_name, str):
        raise TypeError(f"Date column name is not a string. Type given: {type(date_column_name)=}")
    if date_column_name not in data_in.columns:
        raise ValueError(f"{date_column_name=} not found in data_in. Columns available: {list(data_in.columns)}")
    if not np.issubdtype(data_in[date_column_name], np.datetime64):
        raise TypeError(f"Date column in data_in is not a datetime dtype. {type(data_in[date_column_name])=}")
    if bad_cols := set(columns).difference(set(data_in.columns)):
        raise ValueError(f"Columns {bad_cols} are not found in data_in. Columns available: {list(data_in.columns)}")

    # grab the number of days in the date range of data_in
    num_days = (data_in[date_column_name].max() - data_in[date_column_name].min()).days + 1

    coverages = data_in.count()[columns] / num_days

    if isinstance(coverages, pd.Series):
        coverages.index = coverages.index + "_COVERAGE"

    return coverages

def calc_percent_rows_fully_covered(data_in: pd.DataFrame,
                                    columns: str | Iterable[str],
                                    date_column_name: str = 'LOCAL_DATE') -> float:
    """Calculate percentage of days that have data in all columns given

    NOTE: this checks coverage in the date range given in data_in. If rows were
    missing for certain days, those too would penalize coverage score

    Parameters
    ----------
    data_in : pd.DataFrame
        The data to check percent coverage in some of its columns
    columns : str | Iterable[str]
        Column names to check coverage. If multiple names given, each percentage
        will be returned separately
    date_column_name : str
        Name of the date column found in data_in

    Returns
    -------
    float
        the ratio of days that contain data across all columns listed by
        `columns`

    Raises
    ------
    TypeError
        data_in is not a DataFrame
    TypeError
        columns is not a string or iterable string
    ValueError
        The date column of the name date_column_name was not found in data_in
    TypeError
        The date column in data_in is not of a datetime dtype
    ValueError
        Columns given are not found int data_in
    """
    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"data_in was not a pandas DataFrame. Type given: {type(data_in)=}")
    if not isinstance(columns, (str, Iterable)):
        raise TypeError(f"columns given must be a string or iterable of strings. Type given: {type(columns)=}")
    if not isinstance(date_column_name, str):
        raise TypeError(f"Date column name is not a string. Type given: {type(date_column_name)=}")
    if date_column_name not in data_in.columns:
        raise ValueError(f"{date_column_name=} not found in data_in. Columns available: {list(data_in.columns)}")
    if not np.issubdtype(data_in[date_column_name], np.datetime64):
        raise TypeError(f"Date column in data_in is not a datetime dtype. {type(data_in[date_column_name])=}")
    if bad_cols := set(columns).difference(set(data_in.columns)):
        raise ValueError(f"Columns {bad_cols} are not found in data_in. Columns available: {list(data_in.columns)}")

    # grab the number of days in the date range of data_in
    num_days = (data_in[date_column_name].max() - data_in[date_column_name].min()).days + 1

    coverages = data_in[columns].notnull().all(axis=1).sum() / num_days

    if isinstance(coverages, pd.Series):
        coverages.index = coverages.index + "_COVERAGE"
    return coverages

def fill_data_frame_by_plans(data_in: pd.DataFrame, column_fill_plans: dict, rows_to_edit= slice(None)) -> pd.DataFrame:
    """Fill the data frame by a set of plans on the given rows

    This function returns an edit of data_in, with the following entries edited
    data_in.loc[rows_to_edit, column_fill_plans.keys()]. The column_fill_plans
    values contain the rules to make the edit.

    Parameters
    ----------
    data_in : pd.DataFrame
        The data to be edited
    column_fill_plans : dict
        Dictionary with plans to fill in data for newly created rows. A
        dictionary is given where the key is a column name found in data_in and
        the value is either a single value of the dtype that matches the column,
        a function that can be a reducing function along rows (e.g. used with
        ``pd.DataFrame.apply(func, axis =1)``), or a string of the format
        ``method=<method-type>``, where <method-type> is either ``bfill`` for
        back-fill or ``ffill`` for forward-fill, pandas Series filling functions
    rows_to_edit : optional
        The rows with which to edit for data_in, by default all rows will be
        edited. The type can be anything pd.DataFrame.loc can receive in the
        row/index section (i.e. an index value, slice, series, list)

    Returns
    -------
    pd.DataFrame
        The edited dataframe, defined by rows_to_edit and column_fill_plans

    Raises
    ------
    TypeError
        The data_in was not a DataFrame
    """
    if column_fill_plans is None:
        return data_in

    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"data_in was not a pandas DataFrame. Type given: {type(data_in)=}")

    _check_valid_fill_plans(data_in=data_in, column_fill_plans=column_fill_plans)

    if rows_to_edit is None:
        rows_to_edit = slice(None) # What's the best way to default to select all?

    data_out = data_in.copy()

    for col, plan in column_fill_plans.items():
        # if the plan given was a function, try to apply it to data_out
        if callable(plan):
            data_out.loc[rows_to_edit, col] = data_out.loc[rows_to_edit].apply(plan, axis=1)
            continue

        # if a fillna method was given, call fillna on the rows we asked to fill
        if isinstance(plan, str):
            potential_method = plan.split('=')

            # check if this string had an = and that to the left of the = was 'method'
            if (len(potential_method) == 2) and potential_method[0].strip() == 'method':
                method_type = potential_method[1].strip()
                if method_type == 'bfill':
                    data_out[col] = data_out[col].bfill()
                elif method_type == 'ffill':
                    data_out[col] = data_out[col].ffill()
                else:
                    raise ValueError(f"Unknown method type {method_type}." \
                                     " Supported method types are 'bfill' and 'ffill'.")
                # The above may have edited rows we didn't want to edit. Let's reverse it
                rows_to_exclude = data_out.index.difference(data_out.loc[rows_to_edit,].index)
                data_out.loc[rows_to_exclude,col] = data_in.loc[rows_to_exclude,col]
                continue

        # default is to fill all with the object in plan
        data_out.loc[rows_to_edit, col] = plan

    return data_out

def list_missing_days(data_in: pd.DataFrame, date_column_name: str = 'LOCAL_DATE') -> pd.DatetimeIndex:
    """Report a list of days that are missing from the dataset

    Parameters
    ----------
    data_in : pd.DataFrame
        The data for which the dates are to be inspected
    date_column_name : str
        The name of the date column to inspect

    Returns
    -------
    pd.DatetimeIndex
        The days missing from data that came in

    """
    if not isinstance(data_in, pd.DataFrame):
        raise TypeError(f"The given data is is not a pandas DataFrame. Type given: {type(data_in)}")
    if not isinstance(date_column_name, str):
        raise TypeError(f"The date column name is not a string. Type given: {type(date_column_name)=}")
    if date_column_name not in data_in.columns:
        raise ValueError(f"{date_column_name=} not found in data_in. Columns available: {list(data_in.columns)}")

    dates_in = data_in.sort_values(by=date_column_name, ascending=True)[date_column_name]
    return pd.date_range(start=dates_in.iloc[0], end=dates_in.iloc[-1]).difference(dates_in)
