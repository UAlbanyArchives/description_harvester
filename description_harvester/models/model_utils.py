def filter_empty_fields(obj):
    """
    Recursively filters out empty fields from a given object or list.
    """
    if isinstance(obj, dict):
        # If obj is a dictionary, filter out empty values
        return {k: filter_empty_fields(v) for k, v in obj.items() if v not in [None, '', [], {}]}
    elif isinstance(obj, list):
        # If obj is a list, recursively filter each item
        return [filter_empty_fields(v) for v in obj if v not in [None, '', [], {}]]
    else:
        # If it's a basic value (not a list or dict), return it
        return obj
        