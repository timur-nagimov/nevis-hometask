"""A stand-in for anthropic.Anthropic: records each request, then returns a canned answer or raises."""

import json
from collections.abc import Callable
from typing import Any

import httpx2
from anthropic.types import Message, TextBlock, Usage

REQUEST = httpx2.Request('POST', 'https://api.anthropic.com/v1/messages')  # the SDK's errors need one
Outcome = Message | Exception | Callable[[], Message]


def answer(**changes: Any) -> dict[str, Any]:
    """A well-formed answer for an electricity bill; keyword arguments replace fields."""
    return {
        'summary': 'Electricity bill from Northmoor Energy for March: 95.47 GBP due by 14 April.',
        'concepts': ['proof of address'],
        'document_type': 'utility bill',
        'phrases': ['energy bill', 'address evidence'],
    } | changes


def message(body: dict[str, Any] | str, stop_reason: str = 'end_turn') -> Message:
    """Claude's response with `body` as its text: a dict as JSON, a string as it is."""
    response = Message(
        id='msg_fake',
        content=[TextBlock(type='text', text=body if isinstance(body, str) else json.dumps(body))],
        model='claude-haiku-5-5',
        role='assistant',
        stop_reason=stop_reason,
        stop_sequence=None,
        type='message',
        usage=Usage(input_tokens=1500, output_tokens=200),
    )
    response._request_id = 'req_fake'  # the SDK sets it on every response it returns
    return response


class FakeMessages:
    def __init__(self, outcome: Outcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        if isinstance(self.outcome, Message):
            return self.outcome
        return self.outcome()


class FakeClaude:
    """The only part of anthropic.Anthropic that the enrichment uses: client.messages.create(**kwargs)."""

    def __init__(self, outcome: Outcome) -> None:
        self.messages = FakeMessages(outcome)
