#!/usr/bin/env python
"""Describe file"""
import re
from collections import OrderedDict

# The first part that matches one of these types is parsed for construction data
from datetime import datetime

sm = staticmethod


MIMETYPES = [
    'text/plain',
    'text/html'
]


def fmtyday(dt):
    return dt.strftime("%Y%j")


# TODO this belongs in the parameter file
# bounds = min, max
LON_BOUNDS = -180.0, -50.0
LAT_BOUNDS = -20.0, 80.0
ELEV_BOUNDS_m = -500.0, 9000.0
TEMPORAL_BOUNDS = datetime(2000, 1, 1), datetime(2100, 1, 1)

FT_M = 0.3048


class BoundsChecker(object):
    def __init__(self, bounds):
        self.min, self.max = bounds

    def __contains__(self, value):
        return self.min <= value < self.max


class bounds:
    lon = BoundsChecker(LON_BOUNDS)
    lat = BoundsChecker(LAT_BOUNDS)
    elevation = BoundsChecker(ELEV_BOUNDS_m)
    temporal = BoundsChecker(TEMPORAL_BOUNDS)


class ParserError(Exception): pass
class ConversionError(ParserError): pass
class ValidationError(ParserError): pass
class RequiredFieldsNotFound(ParserError): pass




class ConstructionReport(object):
    def __init__(self, sta=None, year=None, month=None, day=None, lddate=None, elev=None,
                 unit=None, lat=None, lon=None, epoch=None, yday=None):
        self._rec = OrderedDict([
            ('sta', sta),
            ('year', year),
            ('month', month),
            ('day', day),
            ('lddate', lddate),
            ('elev', elev),
            ('unit', unit),
            ('lat', lat),
            ('lon', lon),
            ('epoch', epoch),
            ('yday', yday),
        ])


_fields = []


def field(klass):
    klass.pattern = re.compile(klass.pattern, re.I)
    _fields.append(klass)
    return klass


class Field(object):
    pattern = None
    required = True

    def __init__(self):
        raise Exception("singleton; do not instantiate")

    @staticmethod
    def convert(m):
        raise Exception("Must override")

    @staticmethod
    def validate(value):
        return True


@field
class StationCode(Field):
    pattern = 'Station Code.*?:\s*(?:(?P<net>\S+)?\s*[_.]\s*)?(?P<sta>\S+)'
    convert = sm(lambda m: m.group('net', 'sta'))


@field
class Date(Field):
    pattern = 'date\s*(?:=|:).*\D(?P<month>\d+)(?P<sep>\D)(?P<day>\d+)(?P=sep)(?P<year>\d+)'
    validate = sm(lambda v: v in bounds.temporal)

    @staticmethod
    def convert(m):
        year, month, day = [int(v) for v in m.group('year', 'month', 'day')]
        year = year if year > 99 else year + 2000
        return datetime(year, month, day)


meters = dict(m=1, km=1000, ft=FT_M)


@field
class Elevation(Field):
    pattern = 'Elevation.*?:\s*(?P<elev>[-.\d]+)\s*(?P<units>\w+)'
    convert = sm(lambda m: float(m.group('elev')) * meters[m.group('units').lower()])
    validate = sm(lambda v: v in bounds.elevation)


@field
class Coords(Field):
    pattern = '(?:gps|coordinates)\s*(?:=|:)\s*(?P<lat>[-.\d]+),\s*(?P<lon>[-.\d]+)'
    convert = sm(lambda m: tuple([float(deg) for deg in m.group('lon', 'lat')]))
    validate = sm(lambda v: v[0] in bounds.lon and v[1] in bounds.lat)


def process(lines):
    output = OrderedDict()
    for line in lines:
        for field in _fields:
            m = field.pattern.match(line)
            if m:
                try:
                    v = field.convert(m)
                except Exception, e:
                    raise ConversionError(field, line, e)
                if not field.validate(v):
                    raise ValidationError(field, v)
                output[field] = v
    missing = set([f for f in _fields if f.required]) - set(output.keys())
    if missing:
        raise RequiredFieldsNotFound(missing)
    return output