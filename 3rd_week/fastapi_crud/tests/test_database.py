from database import get_db


def test_get_db_yields_and_closes_session():
    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        next(gen)
        assert False, "generator should be exhausted"
    except StopIteration:
        pass
