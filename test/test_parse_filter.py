from imgdb.util import parse_filter_expr


def _basic_assert(parsed):
    assert (len(parsed) == 1)
    assert (len(parsed[0]) == 3)
    assert (parsed[0][0] == 'date')
    assert (parsed[0][2] == '2020')


def test_simple_expr():
    parsed = parse_filter_expr('date = 2020')
    _basic_assert(parsed)


def test_multi_expr():
    parsed = parse_filter_expr(['date = 2020'])
    _basic_assert(parsed)


def test_spaces():
    parsed = parse_filter_expr('date   =   2020    ;;')
    _basic_assert(parsed)
    parsed = parse_filter_expr('   date  ==   2020 , ')
    _basic_assert(parsed)
