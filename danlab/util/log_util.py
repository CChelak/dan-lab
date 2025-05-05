"""Utility functions to tune logging
"""

from contextlib import contextmanager
import logging

@contextmanager
def disable_all_logging(highest_level: int = logging.CRITICAL):
    """A context manager that will prevent any logging messages triggered during
    the body from being processed.

    Parameters
    ----------
    highest_level : int, optional
        the maximum logging level in use; by default logging.CRITICAL
    """
    previous_level = logging.root.manager.disable

    logging.disable(highest_level)

    try:
        yield
    finally:
        logging.disable(previous_level)
