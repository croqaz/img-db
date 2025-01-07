from imgdb.util import parse_query_expr


def _basic_assert(parsed):
    assert len(parsed) == 1
    assert len(parsed[0]) == 3
    assert parsed[0][0] == 'date'
    assert parsed[0][2] == '2020'


def test_simple_expr():
    parsed = parse_query_expr('date = 2020')
    _basic_assert(parsed)


def test_spaces():
    parsed = parse_query_expr('date   =   2020    ;;')
    _basic_assert(parsed)
    parsed = parse_query_expr('   date  ==   2020 , ')
    _basic_assert(parsed)


def test_multi_expr():
    parsed = parse_query_expr(['date = 2020; bytes > 1000'])
    assert len(parsed) == 2
    assert len(parsed[0]) == 3
    assert len(parsed[1]) == 3

    assert parsed[0][0] == 'date'
    assert parsed[0][2] == '2020'
    assert parsed[1][0] == 'bytes'
    assert parsed[1][2] == 1000
