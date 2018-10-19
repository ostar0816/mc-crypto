import re
import json
import decimal
import datetime
import bson

NON_ALPHA_RE = re.compile(f'[^a-z]')


def _slug(name: str) -> str:
    return NON_ALPHA_RE.sub('-', name.lower())


def objects_default(o):
    if isinstance(o, bson.decimal128.Decimal128):
        return str(o.to_decimal())
    if isinstance(o, decimal.Decimal):
        return str(o)
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    raise TypeError(f'unserializable object {o} of type {type(o)}')


class ObjectsEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        kwargs['default'] = objects_default
        super().__init__(**kwargs)


def make_query_filter(strict, incl_exch, incl_curr, minvol):
    incl = make_include_exact(incl_exch, 'exchanges_slug', strict=True)
    incl2 = make_include_exact(incl_curr, 'currencies', strict=strict)
    vol = make_vol_filter(minvol, 'minvol')
    filters = [f for f in (incl, incl2, vol) if f]
    if not len(filters):
        return {}
    elif len(filters) == 1:
        return filters[0]
    else:
        return {'$and': filters}


def make_include_regex(incl, field):
    if not incl:
        return {}
    regexes = map(_fnmatch_translate, incl)
    return {
        '$or': [{field: {'$regex': re.compile(r, re.I)}}
                for r in regexes],
    }


def make_include_exact(incl, field, strict=True):
    if not incl or not isinstance(incl, list):
        return {}
    if strict:
        field = f'${field}'
        return {'$expr': {'$setIsSubset': [field, incl]}}
    return {field: {'$in': incl}}


def make_vol_filter(vol, field):
    if not vol:
        return {}
    vol = decimal.Decimal(vol)
    if vol <= 0:
        return {}
    return {field: {'$gt': bson.Decimal128(vol)}}


def _fnmatch_translate(pat):
    '''Translate a shell PATTERN to a regular expression.
    There is no way to quote meta-characters.
    '''

    res = []
    for c in pat:
        res.append('.*' if c == '*' else re.escape(c))
    res = ''.join(res)
    return r'(?:%s)\Z' % res
