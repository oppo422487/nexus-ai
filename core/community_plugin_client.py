"""Adapt community one-shot requests to Mark's model fallback and deadlines."""
from core import gemini


class Client:
    def __init__(self, api_key=None):
        self.key = api_key or ''
        self.models = self

    def generate_content(self, model=None, contents=None, config=None, **kwargs):
        response = gemini.call(contents, tier=gemini.SMART, config=config,
                               timeout_ms=30000, key=self.key)
        if response is None:
            raise RuntimeError('No configured model answered; check provider/quota.')
        return response
