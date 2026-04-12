from RAG.generation.prompts import build_messages


def test_build_messages_no_history():
    messages = build_messages(question="What is X?", context="[1] X is a thing.")
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert "What is X?" in messages[-1]["content"]
    assert "[1] X is a thing." in messages[-1]["content"]


def test_build_messages_with_history():
    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    messages = build_messages("Follow-up?", "context", history)
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]


def test_build_messages_empty_context():
    messages = build_messages("What?", "")
    assert len(messages) == 2
