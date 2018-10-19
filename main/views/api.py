import json

import pymongo
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from romulus import MG

from main.datatables import CustomDataTables
from main.utils import ObjectsEncoder, make_query_filter
from main.views import db


MAX_ROWS = 10000
MAX_API_RESULTS = 100


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def table(request, collection='simul'):
    if collection != 'simul' or 'args' not in request.GET:
        return JsonResponse({})
    request_args = json.loads(request.GET['args'])
    custom_filter = make_query_filter(
        False,
        request_args['incl-exch'],
        request_args['incl-curr'],
        request_args['minvol'],
    )
    results = CustomDataTables(
        db, collection, MAX_ROWS, request_args, custom_filter,
    ).get_rows()
    return JsonResponse(results, encoder=ObjectsEncoder)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def top_trades(request):
    limit = min(int(request.GET.get('limit', MAX_API_RESULTS)), MAX_API_RESULTS)
    minvol = request.GET.get('minvol')
    strict = _process_boolean(request.GET.get('strict'))
    incl_exch = _process_list(request.GET.get('incl-exch'))
    incl_curr = _process_list(request.GET.get('incl-curr'))
    query = make_query_filter(strict, incl_exch, incl_curr, minvol)
    trades_data = list(db.simul.find(
        query,
        {'_id': False, 'base': False, 'base_market': False, 'arbitrage': False,
         'simulations': False, 'exchanges': False, 'books': False},
    ).sort([('spread', pymongo.DESCENDING)]).limit(limit))
    trades_data = {'data': trades_data}
    return JsonResponse(trades_data, encoder=ObjectsEncoder)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def fees(request):
    exchange = request.GET.get('exchange')
    if exchange is None:
        return JsonResponse({'error': 'no exchange provided'})
    try:
        exch = MG.get(exchange)
        res = {
            'taker_fee': exch['taker_fee'],
            'maker_fee': exch['maker_fee'],
        }
    except KeyError:
        res = {'error': f'no such exchange: {exchange}'}
    return JsonResponse(res)


def _process_list(value):
    if value is None:
        return []
    return value.split(',')


def _process_boolean(value):
    if value is None:
        return False
    return value == 'true'
