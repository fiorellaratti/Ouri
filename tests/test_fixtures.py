from ouri.api.fixtures import list_fixtures, load_fixture
from ouri.engine.rules import evaluate


def test_all_fixtures_load_and_evaluate():
    files = list_fixtures()
    assert len(files) >= 6
    for path in files:
        snap = load_fixture(path)
        decision = evaluate(snap)
        assert decision.state is not None
