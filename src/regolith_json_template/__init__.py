from copy import deepcopy, copy
import uuid
import math
import random
from typing import Any, NamedTuple

VERSION = (1, 3, 0)
__version__ = '.'.join([str(x) for x in VERSION])

EVAL_STRING_OPEN = '`'
EVAL_STRING_CLOSE = '`'
LIST_UNPACK_KEY = '__unpack__'
LIST_UNPACK_OPTIONAL_VALUE = '__value__'

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

class JsonTemplateJoinStr:
    '''
    A data class used during the evalution of the template as a first item
    of a list of strings to join and convert to one string. In JSON files
    this class is known as "JoinStr" to reduce the amount of characters
    '''
    def __init__(self, join_str: str):
        self.join_str = join_str

class _Unpack(NamedTuple):
    '''
    _Unpack is an object that is used internally by the eval_json function to
    pass lists to be unpacked up from an item of the list, to the list itself.
    The value of the _Unpack object is a list of values to unpack.
    '''
    data: list[Any]

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


def eval_json(data, scope: dict[str, Any], _is_list_item: bool = False):
    '''
    Walks JSON file (data) yields json paths. The behavior of the function is
    undefined if the data contains objects that can't be represended as JSON
    using json.dumps (e.g. sets, functions, etc.).

    :param data: JSON data to be evaluated.
    :param scope: A dictionary that will be used as a scope for evaluating
        the template.
    :param _is_list_item: An internally used flag that indicates if the data
        is a list item. List items can be unpacked into multiple items in
        some cases.
    '''
    if isinstance(data, dict):
        keys: list[tuple[str, None | list[str | JsonTemplateK]]] = []
        is_unpacked = False
        for k in data.keys():
            if k == LIST_UNPACK_KEY and _is_list_item:
                is_unpacked = True
                continue
            is_eval_key, stripped_key = is_eval_string(k)
            if is_eval_key:
                keys.append((k, eval_key(stripped_key, scope)))
            else:
                keys.append((k, None))

        if is_unpacked:
            scopes: list[dict[str, Any]]
            if isinstance(data[LIST_UNPACK_KEY], list):
                scopes = data[LIST_UNPACK_KEY]
            elif isinstance(data[LIST_UNPACK_KEY], str):
                is_unpak_eval_val, unpack_eval_val = is_eval_string(
                    data[LIST_UNPACK_KEY])
                if not is_unpak_eval_val:
                    raise JsonTemplateException(
                        f"The value of {LIST_UNPACK_KEY} must be a list or "
                        "an eval string.")
                scopes = eval_value(unpack_eval_val, scope)
            del data[LIST_UNPACK_KEY]
            if LIST_UNPACK_OPTIONAL_VALUE in data:
                if len(data) > 1:
                    raise JsonTemplateException(
                        f"{LIST_UNPACK_OPTIONAL_VALUE} can't be used with "
                        "other keys.")
                data_template = data[LIST_UNPACK_OPTIONAL_VALUE]
                del data[LIST_UNPACK_OPTIONAL_VALUE]
            else:
                data_template = data
            data = _Unpack([])
            for i, scope in enumerate(scopes): 
                if i == len(scopes) - 1:
                    # No need to copy the last item, we can simply use the
                    # original data_template (we don't need it anymore).
                    data.data.append(eval_json(data_template, scope))
                else:
                    data.data.append(eval_json(deepcopy(data_template), scope))
        else:
            for k, evaluated_keys in keys:
                if isinstance(evaluated_keys, list):
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
                        evaluated_value = eval_json(
                            data[evaluated_key], child_scope)
                        # Ellipsis (...) is used as no value indicator.
                        if evaluated_value != ...:
                            data[evaluated_key] = evaluated_value
                        elif evaluated_key in data:
                            del data[evaluated_key]
                else:
                    evaluated_value = eval_json(data[k], scope)
                    # Ellipsis (...) is used as no value indicator.
                    if evaluated_value != ...:
                        data[k] = evaluated_value
                    elif k in data:
                        del data[k]
    elif isinstance(data, list):
        join_strings: JsonTemplateJoinStr | None = None
        new_data = []
        for i, item in enumerate(data):
            eval_item = eval_json(item, scope, True)
            if isinstance(eval_item, _Unpack):
                if (
                        i == 0 and len(eval_item.data) > 0 and
                        isinstance(eval_item.data[0], JsonTemplateJoinStr)):
                    join_strings = eval_item.data[0]
                    new_data.extend(eval_item.data[1:])
                else:
                    new_data.extend(eval_item.data)
            elif i == 0 and isinstance(eval_item, JsonTemplateJoinStr):
                join_strings = eval_item
            else:
                new_data.append(eval_item)
        if join_strings is not None:
            try:
                new_data = join_strings.join_str.join(new_data)
            except TypeError as e:
                raise JsonTemplateException(
                    "Can't join non-string values using 'JoinStr'.") from e
        data = new_data
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
    "random": random, "K": JsonTemplateK, "JoinStr": JsonTemplateJoinStr}
'''
The default socpe to be merged with the scope passed by the user in the regolith
filter.
'''
