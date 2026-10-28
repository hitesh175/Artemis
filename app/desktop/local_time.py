"""Local timezone rules, rather than a snapshot of the current UTC offset."""
from datetime import datetime
import os


def local_timezone():
    if os.name=='nt':
        from dateutil.tz import tzwinlocal
        return tzwinlocal()
    from dateutil.tz import gettz
    zone=gettz.nocache()
    if zone is None:raise RuntimeError('The local timezone could not be determined.')
    return zone


def local_now():
    return datetime.now(local_timezone())
