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
    ),
    (
        [  # source
            {
                "my_favourite_color": "I don't know"
            },
            {
                "__unpack__": [{"color": "red"}, {"color": "green"}],
                "my_favourite_color": "`color.upper()`"
            },
            {
                "my_favourite_color": "BLACK"
            }
        ],
        [  # expected
            {
                "my_favourite_color": "I don't know"
            },
            {
                "my_favourite_color": "RED"
            },
            {
                "my_favourite_color": "GREEN"
            },
            {
                "my_favourite_color": "BLACK"
            }
        ]
    ),
    (
        [  # source
            {
                "my_favourite_color": "I don't know"
            },
            {
                "__unpack__": "`[dict(color=c) for c in ('red', 'green')]`",
                "my_favourite_color": "`color.upper()`"
            },
            {
                "my_favourite_color": "BLACK"
            }
        ],
        [  # expected
            {
                "my_favourite_color": "I don't know"
            },
            {
                "my_favourite_color": "RED"
            },
            {
                "my_favourite_color": "GREEN"
            },
            {
                "my_favourite_color": "BLACK"
            }
        ]
    ),
    (
        [  # source
            "It's not green",
            {
                "__unpack__": "`[dict(color=c) for c in ('red', 'green')]`",
                "__value__": "`color == 'green'`"
            },
            "Not green"
        ],
        [  # expected
            "It's not green",
            False,
            True,
            "Not green"
        ]
    ),
])
def test_eval(source, expected):
    scope = DEFAULT_SCOPE | {'foo': 12345}
    assert eval_json(source, scope) == expected
