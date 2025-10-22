def filter_empty_fields(obj):
    """
    Recursively filters out empty fields from a nested data structure.
    Empty values are defined as: None, '', [], {}
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
        
def to_struct_with_custom_fields(obj):
    """
    Builds a dictionary representation of an object, including dynamic and nested data.
    Includes custom fields as attributes.
    
    This function:
    - Converts the object using its `to_struct()` method
    - Merges in any `custom_fields` present on the object
    - Recursively applies the same logic to objects in a `components` list (if present)

    Args:
        obj (object): An object with `to_struct()`, and optionally `custom_fields` and `components`.

    Returns:
        dict: A fully populated dictionary representation of the object.
    """
    data = dict(obj.to_struct() or {})

    if hasattr(obj, 'custom_fields'):
        data.update(obj.custom_fields)

    if hasattr(obj, 'components') and isinstance(obj.components, list):
        data['components'] = [
            to_struct_with_custom_fields(c) if hasattr(c, 'to_struct') else c
            for c in obj.components
        ]

    return data