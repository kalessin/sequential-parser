def yield_all_dicts(data):
    """
    Travel all the hierarchy of the given highly structured dict/list, starting from highest level, and yield every dict in all depths
    """
    if isinstance(data, dict):
        yield data
        for val in data.values():
            for result in get_all_dicts(val):
                yield result
    elif isinstance(data, list):
        for val in data:
            for result in get_all_dicts(val):
                yield result
