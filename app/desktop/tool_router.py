"""Ordered, deterministic tools. Model output is never an execution request."""
from dataclasses import dataclass
import logging
from typing import Callable

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    execute: Callable[[str], dict]


class ToolRouter:
    """First handled result wins; tool failures never fall through to chat/actions.

    Results always include handled, reply, spoken_reply, tool, and sources.
    Existing fields (confirmation, weather_choices, launched, ok) are preserved.
    handled means ownership of the request, not successful completion.
    Sources are supplied by tools, never inferred from request keywords.
    """
    def __init__(self, tools):
        self._tools = tuple(tools)
        names = [tool.name for tool in self._tools]
        if len(names) != len(set(names)):
            raise ValueError('Tool names must be unique')

    def catalog(self):
        return [{'name': t.name, 'description': t.description} for t in self._tools]

    @staticmethod
    def result(raw, name):
        if not isinstance(raw, dict) or type(raw.get('handled')) is not bool:
            raise ValueError('Tool must return a handled flag')
        if not raw['handled']:
            return dict(handled=False, reply='', spoken_reply='', tool=None, sources=[])
        reply = raw.get('reply')
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError('Handled result requires a reply')
        spoken = raw.get('spoken_reply', reply)
        sources = raw.get('sources', [])
        if not isinstance(spoken, str) or not isinstance(sources, list):
            raise ValueError('Invalid speech or source metadata')
        return {**raw, 'tool': name, 'spoken_reply': spoken, 'sources': sources}

    def execute(self, text):
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 3000:
            return self.result(dict(handled=True, ok=False,
                                    reply='Enter a request of 1–3000 characters.'), 'router')
        for tool in self._tools:
            try:
                result = self.result(tool.execute(text), tool.name)
            except Exception:
                LOG.exception('Tool failed: %s', tool.name)
                return self.result(dict(handled=True, ok=False,
                                        reply='Artemis could not complete that request. Please try again.'), tool.name)
            if result['handled']:
                return result
        return self.result({'handled': False}, None)
