"""The transport conformance table, run against every adapter in the repo.

``UrllibTransport`` runs the full table in front of a raw loopback socket —
the first test in either port to put a production adapter in front of one.
``FakeTransport`` runs the response rows, so the double cannot drift into a
shape the real adapter is unable to produce.
"""

from __future__ import annotations

import pytest

from ghagen.pin.github import UrllibTransport
from tests.test_pin.transport_contract import (
    ALL_CASES,
    RESPONSE_CASES,
    ResponseCase,
    assert_transport_contract,
    canned_adapter,
    case_id,
    loopback_adapter,
)


@pytest.mark.parametrize("case", ALL_CASES, ids=case_id)
def test_urllib_transport_conforms(case: ResponseCase | str) -> None:
    assert_transport_contract(
        loopback_adapter(lambda deadline: UrllibTransport(timeout=deadline)),
        cases=[case],
    )


@pytest.mark.parametrize("case", RESPONSE_CASES, ids=case_id)
def test_fake_transport_conforms(case: ResponseCase) -> None:
    assert_transport_contract(canned_adapter(), cases=[case])
