"""Keep the private class roster out of chatbot and model context objects."""


def without_classmates(value):
    """Copy structured context, omitting roster sections at any nesting level."""
    if isinstance(value, dict):
        return {key: without_classmates(item) for key, item in value.items()
                if not isinstance(key, str) or key.casefold() != 'classmates'}
    if isinstance(value, (list, tuple)):
        return [without_classmates(item) for item in value]
    return value
