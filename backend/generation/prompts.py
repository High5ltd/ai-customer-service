SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions based on the provided context documents.

Rules:
1. Answer ONLY based on the context provided below. Do not use prior knowledge.
2. Cite your sources using [N] notation (e.g., [1], [2]) after each statement.
3. If the answer cannot be found in the context, say: "I don't have enough information in the provided documents to answer this question."
4. Be concise and accurate. Use bullet points or numbered lists when appropriate.
5. Do not make up information or speculate beyond what the documents say.
"""

CONTEXT_PROMPT_TEMPLATE = """\
Context documents:
{context}

Question: {question}

Answer (with citations):"""


def build_messages(
    question: str,
    context: str,
    history: list[dict] | None = None,
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    user_content = CONTEXT_PROMPT_TEMPLATE.format(context=context, question=question)
    messages.append({"role": "user", "content": user_content})

    return messages
