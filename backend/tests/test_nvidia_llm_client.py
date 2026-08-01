"""Unit tests for the Groq LangChain adapter without network access."""

import os
import sys
from types import ModuleType

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.llm_client import LangChainGroqClient


class _FakeChain:
    def __init__(self, result: str) -> None:
        self.result = result
        self.inputs: list[dict[str, str]] = []

    def invoke(self, values: dict[str, str]) -> str:
        self.inputs.append(values)
        return self.result

    def stream(self, values: dict[str, str]):
        self.inputs.append(values)
        yield "first "
        yield "second"


def test_groq_client_uses_api_key_and_a_string_output_chain(monkeypatch) -> None:
    captured: dict[str, object] = {}
    chain = _FakeChain("grounded answer")

    class FakeChatGroq:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        def __ror__(self, _prompt):
            return self

        def __or__(self, _parser):
            return chain

    class FakePrompt:
        def __or__(self, _model):
            return FakeChatGroq()

    class FakePromptTemplate:
        @staticmethod
        def from_template(template: str) -> FakePrompt:
            captured["template"] = template
            return FakePrompt()

    groq_module = ModuleType("langchain_groq")
    groq_module.ChatGroq = FakeChatGroq
    parser_module = ModuleType("langchain_core.output_parsers")
    parser_module.StrOutputParser = lambda: object()
    prompts_module = ModuleType("langchain_core.prompts")
    prompts_module.PromptTemplate = FakePromptTemplate
    monkeypatch.setitem(sys.modules, "langchain_groq", groq_module)
    monkeypatch.setitem(sys.modules, "langchain_core.output_parsers", parser_module)
    monkeypatch.setitem(sys.modules, "langchain_core.prompts", prompts_module)

    client = LangChainGroqClient("test-key", "llama-3.3-70b-versatile")

    assert captured["groq_api_key"] == "test-key"
    assert captured["model"] == "llama-3.3-70b-versatile"
    assert client.chat("Use cited evidence.", "What changed?") == "grounded answer"
    assert list(client.chat_stream("Use cited evidence.", "What changed?")) == [
        "first ",
        "second",
    ]
