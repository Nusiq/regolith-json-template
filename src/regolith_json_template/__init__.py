from itertools import chain
from copy import deepcopy, copy
import uuid
import math
from pathlib import Path
from typing import Any

VERSION = (1, 0, 0)
__version__ = '.'.join([str(x) for x in VERSION])

EVAL_STRING_OPEN = '`'
EVAL_STRING_CLOSE = '`'

class JsonTemplateException(Exception):
    '''Root exception for json_template.'''
    pass


class JsonTemplateK:
    '''
    A data class used during the evalution of the template in eval_key to
    pass the key value and extend the scope. In JSON files this class is
    known as "K" to reduce the amount of characters needed to write the
    template.
    '''

    def __init__(self, __key: str, **kwargs):
        self.key: str = __key
        self.scope_extension: dict[str, Any] = kwargs


def is_eval_string(text: str) -> tuple[bool, str]:
    '''
    Checks if text is a string to be evaluated and returns the result and the
    substring to be evaluated. An eval string is a string that starts with
    EVAL_STRING_OPEN and ends with EVAL_STRING_CLOSE (global variables).

    If it's not an eval string, returns False and the original text.
    '''
    if len(text) <= len(EVAL_STRING_OPEN) + len(EVAL_STRING_CLOSE):
        return False, text  # Too short to be an eval string
    if text.startswith(EVAL_STRING_OPEN) and text.endswith(EVAL_STRING_CLOSE):
        return True, text[len(EVAL_STRING_OPEN):-len(EVAL_STRING_CLOSE)]
    return False, text


def eval_json(data, scope: dict[str, Any]):
    '''
    Walks JSON file (data) yields json paths. The behavior of the function is
    undefined if the data contains objects that can't be represended as JSON
    using json.dumps (e.g. sets, functions, etc.).
    '''
    if isinstance(data, dict):
        keys = list(data.keys())
        for k in keys:
            is_eval_key, key = is_eval_string(k)
            if is_eval_key:
                evaluated_keys = eval_key(key, scope)
                old_data_k_value = data[k]
                del data[k]
                last_item_index = len(evaluated_keys) - 1
                for i, evaluated_key in enumerate(evaluated_keys):
                    child_scope = scope  # No need for deepcopy
                    if isinstance(evaluated_key, JsonTemplateK):
                        child_scope = scope | evaluated_key.scope_extension
                        evaluated_key = evaluated_key.key
                    # Don't copy the last item, simply use the old value. Note
                    # that it must be the last item not for example the first
                    # one, because the next item always is based on the
                    # old_data_k_value so it can't be evaluated when it needs
                    # to be a source for other items.
                    if i == last_item_index:
                        data[evaluated_key] = old_data_k_value
                    else:  # copy the rest
                        data[evaluated_key] = deepcopy(old_data_k_value)
                    data[evaluated_key] = eval_json(
                        data[evaluated_key], child_scope)
            else:
                data[k] = eval_json(data[k], scope)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = eval_json(data[i], scope)
    elif isinstance(data, str):
        is_eval_val, data = is_eval_string(data)
        if is_eval_val:
            return eval_value(data, scope)
        return data
    return data


def eval_key(key: str, scope: dict[str, Any]) -> list[str | JsonTemplateK]:
    '''
    Evaluates JSON key using python's eval function. Works on a copy of the
    scope to prevent the scope from being modified.

    The result is always a list of strings or JsonTempalteK objects, which can
    be passed to the eval_json function to provide it with information about
    the furhter evaluation of the JSON file. The JsonTemplateK objects are used
    to extend the scope of the objects nested in this object.
    '''
    evaluated = eval(key, copy(scope))
    if isinstance(evaluated, str):
        return [evaluated]
    elif isinstance(evaluated, list):
        result: list[str | JsonTemplateK] = []
        for eval_item in evaluated:
            if isinstance(eval_item, JsonTemplateK):
                if not isinstance(eval_item.key, str):
                    eval_item.key = str(eval_item.key)
                result.append(eval_item)
            elif isinstance(eval_item, str):
                result.append(eval_item)
            else:
                result.append(str(eval_item))
        return result
    raise JsonTemplateException(
        f"Key \"{key}\" doesn't evaluate to a string or list of strings.")


def eval_value(value: str, scope: dict[str, Any]) -> Any:
    '''
    Evaluates a string using python's eval function. Works on a copy of the
    scope to prevent the scope from being modified.
    '''
    return eval(value, copy(scope))


DEFAULT_SCOPE = {
    'true': True, 'false': False, 'math': math, 'uuid': uuid,
    "K": JsonTemplateK}
'''
The default socpe to be merged with the scope passed by the user in the regolith
filter.
'''
