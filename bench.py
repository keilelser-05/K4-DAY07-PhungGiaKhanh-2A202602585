from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs) -> bool:
        return False

from src.chunking import (
    ChunkingStrategyComparator,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
)
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
)
from src.models import Document
from src.store import EmbeddingStore


CORPUS_DIR = Path(os.getenv("CORPUS_DIR", "data/tuition"))
CHUNK_SIZE = 500
TOP_K = 3


BENCHMARK_QUERIES = [
    {
        "query": "Theo quy định FTU, hạn nộp học phí học kỳ I và học kỳ II là khi nào?",
        "gold": "Học kỳ I chậm nhất ngày 30/11; học kỳ II chậm nhất ngày 31/5 hằng năm.",
        "gold_doc_ids": ["ftu-quy-dinh-thu-nop-hoc-phi"],
        "answer_markers": ["30 tháng 11", "31 tháng 5"],
        "metadata_filter": {"doc_id": "ftu-quy-dinh-thu-nop-hoc-phi"},
    },
    {
        "query": "HUS tính học phí môn học của chương trình đào tạo chuẩn theo công thức nào?",
        "gold": "165.000 đồng/tín chỉ × số tín chỉ × hệ số môn học.",
        "gold_doc_ids": ["hus-quy-dinh-thu-hoc-phi"],
        "answer_markers": ["165.000 đồng/tín chỉ"],
        "metadata_filter": {"doc_id": "hus-quy-dinh-thu-hoc-phi"},
    },
    {
        "query": "Sinh viên VNUA phải đáp ứng điều kiện gì trước khi thanh toán học phí?",
        "gold": "Phải cập nhật thông tin Căn cước công dân trong hồ sơ lý lịch trên hệ thống quản lý đào tạo.",
        "gold_doc_ids": ["vnua-thong-bao-thu-hoc-phi-2026"],
        "answer_markers": ["Căn cước công dân"],
        "metadata_filter": {"doc_id": "vnua-thong-bao-thu-hoc-phi-2026"},
    },
    {
        "query": "Nếu sinh viên VNUA chưa nộp đủ học phí Đợt 1 đúng hạn thì bị xử lý thế nào?",
        "gold": "Không có tên trong danh sách tham dự học phần và bị hủy các học phần Block 1 bắt đầu trước ngày 5/10/2026.",
        "gold_doc_ids": ["vnua-thong-bao-thu-hoc-phi-2026"],
        "answer_markers": ["không có tên trong danh sách tham dự học phần"],
        "metadata_filter": {"doc_id": "vnua-thong-bao-thu-hoc-phi-2026"},
    },
    {
        "query": "Học phí được thu vào thời điểm nào?",
        "gold": "Trong các nguồn dành riêng cho sinh viên: FTU quy định hạn học kỳ I là 30/11, còn VNUA thu Đợt 1 từ 20/7/2026 đến 10/8/2026.",
        "gold_doc_ids": [
            "ftu-quy-dinh-thu-nop-hoc-phi",
            "vnua-thong-bao-thu-hoc-phi-2026",
        ],
        "answer_markers": ["30 tháng 11", "20/7/2026"],
        "metadata_filter": {"audience": "student"},
    },
]


class HeadingChunker:
    """Split Markdown by level-2 headings, then split oversized sections."""

    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        self.chunk_size = chunk_size
        self.fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections = [
            section.strip()
            for section in re.split(r"(?=^##\s+)", text.strip(), flags=re.MULTILINE)
            if section.strip()
        ]

        chunks: list[str] = []
        for section in sections:
            if re.fullmatch(r"#{1,6}\s+.+", section):
                continue

            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            lines = section.splitlines()
            heading = lines[0].strip() if lines and lines[0].startswith("#") else ""
            body = "\n".join(lines[1:]).strip() if heading else section

            if not heading:
                chunks.extend(self.fallback.chunk(body))
                continue

            available_size = max(1, self.chunk_size - len(heading) - 2)
            sub_chunks = RecursiveChunker(chunk_size=available_size).chunk(body)
            chunks.extend(f"{heading}\n\n{sub_chunk}" for sub_chunk in sub_chunks)

        return chunks


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return simple YAML frontmatter metadata and Markdown body."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized.strip()

    parts = normalized.split("---", 2)
    if len(parts) < 3:
        return {}, normalized.strip()

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    return metadata, parts[2].strip()


def load_corpus(corpus_dir: Path) -> list[tuple[Path, dict[str, str], str]]:
    loaded = []
    for path in sorted(corpus_dir.glob("*.md")):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))
        loaded.append((path, metadata, content))
    return loaded


def make_embedder():
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()

    try:
        if provider == "local":
            return LocalEmbedder(model_name=LOCAL_EMBEDDING_MODEL)
        if provider == "openai":
            return OpenAIEmbedder(model_name=OPENAI_EMBEDDING_MODEL)
        if provider == "gemini":
            return GeminiEmbedder(model_name=GEMINI_EMBEDDING_MODEL)
    except Exception as error:
        print(f"Embedding provider '{provider}' failed: {error}")
        print("Falling back to MockEmbedder.")

    return MockEmbedder()


def print_baseline(corpus: list[tuple[Path, dict[str, str], str]]) -> None:
    comparator = ChunkingStrategyComparator()
    print("=== BASELINE ANALYSIS ===")
    for path, _, content in corpus[:3]:
        comparison = comparator.compare(content, chunk_size=CHUNK_SIZE)
        print(f"\n{path.name}")
        for strategy, stats in comparison.items():
            print(
                f"  {strategy:14} count={stats['count']:3} "
                f"avg_length={stats['avg_length']:.1f}"
            )


def build_documents(
    corpus: list[tuple[Path, dict[str, str], str]],
    chunker,
) -> list[Document]:
    documents: list[Document] = []

    for path, frontmatter, content in corpus:
        chunks = chunker.chunk(content)
        for index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={
                        **frontmatter,
                        "doc_id": path.stem,
                        "source": str(path),
                        "chunk_index": index,
                    },
                )
            )

    return documents


def normalize_for_match(text: str) -> str:
    return " ".join(text.casefold().split())


def evaluate_results(item: dict, results: list[dict]) -> dict:
    gold_doc_ids = set(item["gold_doc_ids"])
    document_rank = next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if result["metadata"].get("doc_id") in gold_doc_ids
        ),
        None,
    )

    marker_ranks: list[int] = []
    missing_markers: list[str] = []
    for marker in item["answer_markers"]:
        normalized_marker = normalize_for_match(marker)
        marker_rank = next(
            (
                rank
                for rank, result in enumerate(results, start=1)
                if normalized_marker in normalize_for_match(result["content"])
            ),
            None,
        )
        if marker_rank is None:
            missing_markers.append(marker)
        else:
            marker_ranks.append(marker_rank)

    if missing_markers:
        content_score = 0
        relevant_rank = None
    else:
        relevant_rank = min(marker_ranks)
        content_score = 2 if relevant_rank == 1 else 1

    return {
        "document_rank": document_rank,
        "relevant_rank": relevant_rank,
        "missing_markers": missing_markers,
        "content_score": content_score,
    }


def print_results(results: list[dict]) -> None:
    for rank, result in enumerate(results, start=1):
        preview = " ".join(result["content"].split())[:180]
        print(
            f"  {rank}. score={result['score']:.4f} "
            f"doc_id={result['metadata'].get('doc_id')} "
            f"chunk={result['metadata'].get('chunk_index')}"
        )
        print(f"     {preview}")


def run_benchmark(store: EmbeddingStore) -> None:
    print("\n=== RETRIEVAL BENCHMARK ===")
    total_score = 0

    for number, item in enumerate(BENCHMARK_QUERIES, start=1):
        query = item["query"]
        metadata_filter = item["metadata_filter"]
        results = store.search_with_filter(
            query,
            top_k=TOP_K,
            metadata_filter=metadata_filter,
        )

        print(f"\nQ{number}: {query}")
        print(f"Filter: {metadata_filter}")
        print(f"Gold: {item['gold']}")
        print(f"Gold doc_ids: {item['gold_doc_ids']}")
        print_results(results)

        evaluation = evaluate_results(item, results)
        total_score += evaluation["content_score"]
        print(f"Document-level rank: {evaluation['document_rank']}")
        print(f"Content-level rank: {evaluation['relevant_rank']}")
        print(f"Missing answer markers: {evaluation['missing_markers'] or 'none'}")
        print(f"Retrieval score: {evaluation['content_score']}/2")

    print(f"\nTOTAL CONTENT-LEVEL SCORE: {total_score}/10")


def run_filter_ab(store: EmbeddingStore) -> None:
    item = BENCHMARK_QUERIES[4]
    query = item["query"]

    without_filter = store.search(query, top_k=TOP_K)
    with_filter = store.search_with_filter(
        query,
        top_k=TOP_K,
        metadata_filter=item["metadata_filter"],
    )

    print("\n=== METADATA FILTER A/B — QUERY 5 ===")
    print(f"Query: {query}")
    print("\nA. Without filter")
    print_results(without_filter)
    print("\nB. With audience=student")
    print_results(with_filter)

    without_ids = [result["id"] for result in without_filter]
    with_ids = [result["id"] for result in with_filter]
    print(f"\nTop-3 changed: {without_ids != with_ids}")


def main() -> int:
    if not CORPUS_DIR.exists():
        print(f"Corpus directory not found: {CORPUS_DIR}")
        return 1

    corpus = load_corpus(CORPUS_DIR)
    if not corpus:
        print(f"No Markdown files found in: {CORPUS_DIR}")
        return 1

    print(f"Loaded {len(corpus)} source files from {CORPUS_DIR}")
    print_baseline(corpus)

    # Mỗi thành viên chỉ thay dòng chọn chunker này.
    chunker = HeadingChunker(chunk_size=CHUNK_SIZE)

    documents = build_documents(corpus, chunker)
    embedder = make_embedder()
    store = EmbeddingStore(collection_name="tuition_benchmark", embedding_fn=embedder)
    store.add_documents(documents)

    print(f"\nStrategy: {chunker.__class__.__name__}")
    print(f"Embedding backend: {getattr(embedder, '_backend_name', type(embedder).__name__)}")
    print(f"Loaded chunks: {store.get_collection_size()}")

    run_benchmark(store)
    run_filter_ab(store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
