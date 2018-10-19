import decimal
import datetime
import bson

from mongo_datatables import DataTables


class CustomDataTables(DataTables):
    def __init__(self, db, coll, upper_limit, request_args, custom_filter):
        self._upper_limit = upper_limit
        super().__init__(db, coll, request_args, **custom_filter)

    @property
    def db(self):
        return self.mongo

    @property
    def limit(self):
        _length = self.request_args.get('length', self._upper_limit)
        return min(_length, self._upper_limit)

    @property
    def requested_columns(self):
        return [column['data'] for column in self.request_args.get('columns')
                if column['data'] is not None]

    def _process_value(self, key, value):
        if isinstance(value, bson.decimal128.Decimal128):
            value = value.to_decimal()
        if isinstance(value, decimal.Decimal):
            value = float(round(value, 6))
        if key == 'plan':
            p = []
            for action in value:
                d = {}
                for k, v in action.items():
                    if isinstance(v, datetime.datetime):
                        v = v.isoformat()
                    elif isinstance(v, bson.decimal128.Decimal128):
                        v = str(v.to_decimal())
                    d[k] = v
                p.append(d)
            value = p
        return value

    def results(self):
        _agg = [
                {'$match': self.filter},
                {'$sort': {self.order_column: self.order_dir}},
                {'$skip': self.start},
                {'$project': self.projection}
            ]

        if self.limit:
            _agg.append({'$limit': self.limit})

        _results = list(self.db[self.collection].aggregate(_agg))

        processed_results = []
        for result in _results:
            result = dict(result)
            result['DT_RowId'] = str(result.pop('_id'))

            for key, val in result.items():
                if isinstance(val, (str, float, int, bson.objectid.ObjectId)):
                    result[key] = val
                else:
                    result[key] = self._process_value(key, val)

            processed_results.append(result)

        return processed_results
