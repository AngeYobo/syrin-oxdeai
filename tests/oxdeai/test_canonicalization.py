def test_object_key_ordering():
    from syrin_ext.oxdeai.canonicalize import canonicalize

    input_data = {"b": 1, "a": 2}
    result = canonicalize(input_data)

    assert result == b'{"a":2,"b":1}'