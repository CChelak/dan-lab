"""Tools for finding number of matches to API queries
"""

from logging import getLogger
import requests

logger = getLogger(__name__)

def find_number_matched(url: str, params: dict) -> int:
    """Get number of entries that match the request stated

    Parameters
    ----------
    url : str
        A URL to which to make the API GET request
    params : dict
        The parameters to pass with the GET request

    Returns
    -------
    int
        Number of matches of the GET request
    """
    alt_params = params.copy()
    alt_params['f'] = 'json'
    alt_params['items'] = 1
    alt_params['offset'] = 0

    response = requests.get(url,
                            params=alt_params,
                            timeout=200)

    if response.status_code != 200:
        logger.error("An error occurred when querying number of entries: [%s] %s",
                     response.status_code,
                     response.text)
        return 0

    try:
        response_dict = response.json()

        num_matched = 'numberMatched'
        if num_matched not in response_dict:
            logger.error("Entry '%s' is not found in response.", num_matched)
            return 0

        return response.json()['numberMatched']
    except requests.JSONDecodeError as e:
        logger.error("Failed to decode the JSON file returned by response: %s", e)
        return 0
