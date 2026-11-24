"""The load measurement stops its background probes even when an upload fails."""

import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.integration import test_load as load


def test_failed_upload_stops_and_joins_the_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    stop = threading.Event()
    probes = [Mock(), Mock()]
    monkeypatch.setattr(
        load, 'threading', SimpleNamespace(Event=lambda: stop, Thread=Mock(side_effect=probes))
    )
    monkeypatch.setattr(load, 'call', Mock(return_value=(201, 0.0, b'{"id": "owner"}')))
    executor = Mock()
    executor.map.side_effect = OSError('upload connection lost')
    pool = Mock()
    pool.__enter__ = Mock(return_value=executor)
    pool.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(load, 'ThreadPoolExecutor', Mock(return_value=pool))

    with pytest.raises(OSError, match='upload connection lost'):
        load.test_search_and_health_keep_answering_during_parallel_uploads('http://unused', 'unused')

    assert stop.is_set()
    for probe in probes:
        probe.start.assert_called_once_with()
        probe.join.assert_called_once_with()
