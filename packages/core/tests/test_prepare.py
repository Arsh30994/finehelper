from finehelper_core.dataset.prepare import prepare_dataset
from finehelper_core.enums import DatasetFormat
from finehelper_core.eval.metrics import exact_match, gate_passed
from finehelper_core.recipe import parse_recipe


def test_prepare_openai_chat():
    raw = (
        '{"messages":[{"role":"user","content":"hi"},{"role":"assistant","content":"hello"}]}\n'
        '{"messages":[{"role":"user","content":"hi"},{"role":"assistant","content":"hello"}]}\n'
    ).encode()
    result = prepare_dataset(raw, "t.jsonl", declared_format=DatasetFormat.openai_chat)
    assert result["failed"] is False
    assert result["dropped_dedupe"] == 1
    assert result["row_count"] == 1
    assert result["digest"]
    assert result["split_map"]["train"]["count"] + result["split_map"]["val"]["count"] == 1


def test_prepare_rejects_missing_assistant():
    raw = b'{"messages":[{"role":"user","content":"hi"}]}\n'
    result = prepare_dataset(raw, "t.jsonl")
    assert result["failed"] is True
    assert result["error_count"] >= 1


def test_alpaca_and_gate():
    raw = b'{"instruction":"Say hi","output":"hello"}\n{"instruction":"Say hi","output":"hello there"}\n'
    result = prepare_dataset(raw, "t.jsonl", declared_format=DatasetFormat.alpaca, dedupe=False)
    assert result["row_count"] == 2
    assert exact_match("hello", "hello") == 1.0
    assert gate_passed({"exact_match": 0.9}, {"metric": "exact_match", "min": 0.8})
    assert not gate_passed({"exact_match": 0.2}, {"metric": "exact_match", "min": 0.8})


def test_recipe_roundtrip():
    doc = parse_recipe(
        """
project: support-bot
train:
  backend: dry_run
  base_model: gpt-4.1-mini
"""
    )
    assert doc.project == "support-bot"
    assert doc.train.backend == "dry_run"
