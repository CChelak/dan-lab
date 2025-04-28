"""Code for dealing with Province information
"""

from enum import StrEnum

class ProvinceCode(StrEnum):
    """Province Code

    Below lists all the accepted province codes for input
    """
    AB = 'AB'
    BC = 'BC'
    MB = 'MB'
    NB = 'NB'
    NL = 'NL'
    NS = 'NS'
    NT = 'NT'
    NU = 'NU'
    ON = 'ON'
    PE = 'PE'
    QC = 'QC'
    SK = 'SK'
    YT = 'YT'
