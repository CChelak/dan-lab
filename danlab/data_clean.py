"""Tools for cleaning up data-related DataFrames
"""

from collections.abc import Iterable

import pandas as pd

def reorder_columns_to_match_properties(df: pd.DataFrame, properties: Iterable | None) -> pd.DataFrame:
    """Reorder the columns to match properties

    Any additional columns not listed by properties will be put in front of properties

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to reorder the columns
    properties : Iterable | None
        The properties to which to reorder the columns; if None, do no reindex

    Returns
    -------
    pd.DataFrame
        The dataframe with the reordered properties
    """
    if properties is None:
        return df

    reordered_cols = [col for col in df.columns if col not in properties] + list(properties)
    return df.reindex(columns=reordered_cols)
