"""Tools looking at IDs of climate data
"""
from collections.abc import Iterable
from typing import TypedDict, Union

class IdDict(TypedDict):
    """A dictionary that includes climate ID information
    """
    climate: Union[str, Iterable[str]]
    station: Union[int, Iterable[int]]

def check_is_id_dictionary(ids: IdDict):
    """Check that an ID input was of an IdDict type

    I'm only now learning that there are libraries that do this for me, both
    statically and dynamically. When I find one that works for me, replace this
    and all other type checks in my code with that library

    Parameters
    ----------
    ids : IdDict
        ID dictionary, where the key is either ``climate`` or ``station`` and
        the values are either a single ID or iterable of IDs

    Raises
    ------
    TypeError
        If the keys are not recognized or the values are not of the appropriate type
    """
    if (bad_id_types := set(ids.keys()).difference(set(IdDict.__annotations__.keys()))):
        raise TypeError(f"The following ID types were not recognized {bad_id_types}." \
                        f"Types allowed {set(IdDict.__annotations__.keys())}")
    for key, val in ids.items():
        if key == 'station':
            if not isinstance(val, (int, Iterable)):
                raise TypeError(f"Station IDs must be int or iterable of ints. Type given: {type(val)}")
            if isinstance(val, Iterable):
                for v in val:
                    if not isinstance(v, int):
                        raise TypeError(f"Contents of Station IDs must be integer. Item {v} in {key} is type {type(v)}")
        if key == 'climate':
            if not isinstance(val, (str, Iterable)):
                raise TypeError(f"Climate IDs must be str or iterable of str. Type given: {type(val)}")
            if isinstance(val, Iterable):
                for v in val:
                    if not isinstance(v, int):
                        raise TypeError(f"Contents of Climate IDs must be str. Item {v} in {key} is type {type(v)}")
