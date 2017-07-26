
import collections


def aggregate_namedtuples(data, aggregators, return_tags=True):

    if not data:
        return data

    new_data = {k: (v, {}) for k, v in data.iteritems()}

    tuples = data.values()
    cls = tuples[0].__class__
    fields = cls._fields

    for agg_key, agg_func in aggregators:

        rows_by_key = {}
        tags_by_key = {}

        if isinstance(agg_key, tuple):
            rows_by_key[agg_key[0]] = tuples
            tags_by_key[agg_key[0]] = agg_key[1]

        elif isinstance(agg_key, basestring):
            rows_by_key[agg_key] = tuples

        else:
            for name, row in data.iteritems():
                key = agg_key(name, row)
                if isinstance(key, tuple):
                    rows_by_key.setdefault(key[0], []).append(row)
                    tags_by_key.setdefault(key[0], {}).update(key[1])
                elif key:
                    rows_by_key.setdefault(key, []).append(row)

        for key, rows in rows_by_key.iteritems():
            agg_values = []
            for i, field in enumerate(fields):
                agg_values.append(agg_func(row[i] for row in rows))
            new_data[key] = (
                cls(*agg_values),
                tags_by_key.get(key) or {}
            )

    if return_tags:
        return new_data
    else:
        return {k: v for k, (v, t) in new_data.iteritems()}

