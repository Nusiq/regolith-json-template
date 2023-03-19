from textwrap import dedent
from regolith_json_template import eval_json, DEFAULT_SCOPE
import pytest

@pytest.mark.parametrize('source, expected', [
    (
        {  # source
            "foo": "`2 + 2`",
            "`str(5+5)`": "baz"
        },
        {  # expected
            "foo": 4,
            "10": "baz"
        }
    ),
    (
        {  # source
            "`[f'bar{i}' for i in range(2)]`": "baz"
        },
        {  # expected
            "bar0": "baz",
            "bar1": "baz"
        }
    ),
    (
        {  # source
            "bar": "`foo`"
        },
        {  # expected (the scope must define the 'foo' value as '12345')
            "bar": 12345
        }
    ),
    (
        {  # source
            "`[K(f'foo{i}', number=i) for i in range(2)]`": {
                "bar": "`number`"
            }
        },
        {  # expected
            "foo0": {
                "bar": 0
            },
            "foo1": {
                "bar": 1
            }
        }
    )
])
def test_eval(source, expected):
    scope = DEFAULT_SCOPE | {'foo': 12345}
    assert eval_json(source, scope) == expected
