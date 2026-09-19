from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(
        self,
        store: EmbeddingStore,
        llm_fn: Callable[[str], str],
    ) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(
        self,
        question: str,
        top_k: int = 3,
    ) -> str:
        """
        Retrieve relevant chunks and ask the LLM to answer
        using only the retrieved context.
        """
        results = self.store.search(
            question,
            top_k=top_k,
        )

        # Không gọi LLM nếu kho dữ liệu không có kết quả.
        if not results:
            return (
                "Không tìm thấy thông tin phù hợp "
                "trong cơ sở tri thức."
            )

        context_parts: list[str] = []

        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})

            source = (
                metadata.get("source")
                or metadata.get("source_url")
                or metadata.get("doc_id")
                or result.get("id")
                or "không xác định"
            )

            context_parts.append(
                f"[{index}] Nguồn: {source}\n"
                f"{result['content']}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""Bạn là trợ lý hỏi đáp dựa trên cơ sở tri thức.

Chỉ sử dụng thông tin trong phần NGỮ CẢNH để trả lời câu hỏi.
Không được tự bổ sung hoặc suy đoán thông tin không có trong ngữ cảnh.
Hãy trích dẫn nguồn bằng số thứ tự [1], [2], [3] tương ứng.
Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ rằng không tìm thấy thông tin.

CÂU HỎI:
{question}

NGỮ CẢNH:
{context}

TRẢ LỜI:
"""

        return self.llm_fn(prompt)