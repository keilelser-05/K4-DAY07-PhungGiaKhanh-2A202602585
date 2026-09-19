# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Phùng Gia Khánh
**Nhóm:** G21
**Ngày:** 19/9/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Độ tương tự cosine cao nghĩa là hai vector embedding có hướng gần giống nhau, cho thấy hai câu hoặc đoạn văn có nội dung, ý nghĩa tương đồng.

**Ví dụ có độ tương tự CAO:**

* Câu A: Sinh viên phải hoàn thành học phí trước ngày 30/11.
* Câu B: Hạn cuối thanh toán học phí học kỳ I là cuối tháng 11.
* Tại sao tương đồng: Hai câu sử dụng từ ngữ khác nhau nhưng đều diễn đạt cùng một thông tin về thời hạn nộp học phí.

**Ví dụ có độ tương tự THẤP:**

* Câu A: Sinh viên có thể thanh toán học phí qua ngân hàng.
* Câu B: Thư viện đóng cửa lúc 17 giờ.
* Tại sao khác: Hai câu nói về hai chủ đề khác nhau: một câu về thanh toán học phí, câu còn lại về thời gian hoạt động của thư viện.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine similarity tập trung vào hướng của vector, tức đặc trưng ngữ nghĩa, và ít bị ảnh hưởng bởi độ lớn của vector. Vì vậy, nó phù hợp hơn để so sánh mức độ tương đồng về ý nghĩa giữa các văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> Phép tính:
>
> Bước nhảy giữa hai chunk là:
>
> `500 − 50 = 450`
>
> Số chunk:
>
> `ceil((10.000 − 50) / (500 − 50))`
>
> `= ceil(9.950 / 450)`
>
> `= ceil(22,11)`
>
> `= 23`

> Đáp án: **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Khi overlap tăng lên 100, số chunk là `ceil((10.000 − 100) / (500 − 100)) = ceil(9.900 / 400) = 25 chunks`. Overlap lớn hơn giúp giữ lại ngữ cảnh nằm ở ranh giới giữa các chunk và hạn chế việc câu hoặc ý quan trọng bị cắt đôi, nhưng làm tăng chi phí lưu trữ và embedding.


---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` để tách tại khoảng trắng hoặc xuống dòng nằm sau dấu kết thúc câu, nhờ đó dấu câu vẫn được giữ lại. Các câu được `strip()` rồi gom tối đa theo `max_sentences_per_chunk`; văn bản rỗng trả về `[]`. Cách này chưa xử lý hoàn hảo chữ viết tắt như `TS.`, `v.v.` và số thập phân vì chúng có thể bị nhận nhầm là ranh giới câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử các separator theo thứ tự `\n\n`, `\n`, `. `, khoảng trắng và cuối cùng là chuỗi rỗng. Mảnh vượt quá `chunk_size` tiếp tục được chia bằng separator nhỏ hơn; sau đó các mảnh ngắn liền kề được gom lại đến gần giới hạn để tránh tạo chunk vụn. Các base case gồm văn bản rỗng, mảnh đã đủ ngắn, hết separator và separator rỗng — hai trường hợp cuối chuyển sang cắt cứng theo kích thước.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` biến từng `Document` thành một record gồm `id`, `content`, bản sao `metadata` và embedding; đồng thời bảo đảm metadata luôn có `doc_id` của tài liệu gốc. `search` nhúng câu truy vấn, tính dot product với từng vector đã chuẩn hóa rồi sắp xếp điểm giảm dần và trả tối đa `top_k` kết quả. Vì vector có chuẩn bằng 1 nên dot product tương đương cosine similarity.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc metadata trước khi xếp hạng để các vị trí top-k không bị tài liệu sai điều kiện chiếm mất. Nếu không có filter, hàm dùng toàn bộ record. `delete_document` xóa tất cả chunk có `metadata["doc_id"]` trùng với mã tài liệu gốc và trả `True` khi có ít nhất một record bị xóa, ngược lại trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent truy xuất top-k chunk, đánh số nguồn `[1]`, `[2]`, `[3]` và đưa nội dung cùng đường dẫn nguồn vào phần ngữ cảnh của prompt. Prompt yêu cầu mô hình chỉ dùng thông tin đã truy xuất, trích dẫn đúng số nguồn và nói rõ khi dữ liệu không đủ, giúp giảm bịa đặt và tăng khả năng truy vết. Nếu store rỗng hoặc không có kết quả, agent trả thông báo phù hợp mà không gọi LLM không cần thiết.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
================================================= test session starts =================================================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Files\KL\KL_Edu\Kdata_University\AI Thực chiến\Day 7\K4-L3A-Data-Foundations\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Files\KL\KL_Edu\Kdata_University\AI Thực chiến\Day 7\K4-L3A-Data-Foundations
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED                            [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED                                     [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED                              [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED                               [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED                                    [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED                    [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED                          [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED                           [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED                         [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED                                           [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED                           [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED                                      [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED                                  [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED                                            [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED                   [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED                       [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED                 [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED                       [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED                                           [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED                             [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED                               [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED                                     [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED                          [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED                            [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED                [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED                             [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED                                      [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED                                     [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED                                [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED                            [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED                       [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED                           [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED                                 [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED                           [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED        [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED                      [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED                     [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED         [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED                    [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED             [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED   [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED       [100%]

================================================= 42 passed in 0.07s ==================================================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Hạn nộp học phí học kỳ I và II của FTU là khi nào? | Học kỳ I chậm nhất 30/11, học kỳ II chậm nhất 31/5. | Cao | 0,8586 | Có |
| 2 | HUS tính học phí môn học theo công thức nào? | Học phí bằng 165.000 đồng/tín chỉ × số tín chỉ × hệ số môn học. | Cao | 0,7698 | Có |
| 3 | Sinh viên VNUA cần làm gì trước khi thanh toán? | Sinh viên đủ điều kiện miễn giảm chỉ thanh toán phần còn lại. | Thấp | 0,7365 | Không |
| 4 | Không nộp đủ học phí Đợt 1 thì bị xử lý thế nào? | Sinh viên được miễn giảm chỉ thanh toán phần học phí còn lại. | Thấp | 0,7416 | Không |
| 5 | Học phí được thu vào thời điểm nào? | Sinh viên phải nộp học phí trong các thời hạn quy định. | Cao | 0,8656 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 4 bất ngờ nhất vì chunk không chứa hình thức xử lý khi nộp muộn nhưng vẫn đạt 0,7416. Điều này cho thấy embedding nhận ra sự gần nhau về chủ đề “sinh viên – học phí – thanh toán”, nhưng cosine similarity không bảo đảm chunk chứa đúng dữ kiện cần trả lời. Vì vậy, đánh giá retrieval phải kiểm tra nội dung đáp án thay vì chỉ nhìn điểm số hoặc `doc_id`.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Theo quy định FTU, hạn nộp học phí học kỳ I và học kỳ II là khi nào? | Mục thời hạn: học kỳ I chậm nhất 30/11; học kỳ II chậm nhất 31/5. | 0,8586 | Có | Trả lời đúng hai thời hạn của FTU. |
| 2 | HUS tính học phí môn học của chương trình đào tạo chuẩn theo công thức nào? | Mức thu: 165.000 đồng/tín chỉ × số tín chỉ × hệ số môn học. | 0,7698 | Có | Trả lời đúng công thức tính học phí. |
| 3 | Sinh viên VNUA phải đáp ứng điều kiện gì trước khi thanh toán học phí? | Top-1 nói về miễn, giảm học phí; chunk chứa điều kiện CCCD đứng hạng 2. | 0,7365 | Không trực tiếp | Top-3 vẫn đủ ngữ cảnh để trả lời rằng sinh viên phải cập nhật CCCD trước khi thanh toán. |
| 4 | Nếu sinh viên VNUA chưa nộp đủ học phí Đợt 1 đúng hạn thì bị xử lý thế nào? | Top-1 nói về miễn, giảm; chunk chứa biện pháp xử lý đứng hạng 2. | 0,7416 | Không trực tiếp | Top-3 đủ thông tin để trả lời: không có tên trong danh sách dự học và bị hủy học phần Block 1 theo điều kiện nêu trong thông báo. |
| 5 | Học phí được thu vào thời điểm nào? | Mục thời hạn của FTU, nhưng top-3 không có lịch Đợt 1 của VNUA. | 0,8656 | Một phần | Chỉ trả lời được thời hạn FTU; thiếu mốc VNUA 20/7/2026–10/8/2026 nên câu trả lời chưa đầy đủ. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **4 / 5**

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Tôi học được rằng không có chiến lược chunking tốt nhất cho mọi loại tài liệu. Chunk theo heading giữ được cấu trúc và ý nghĩa của văn bản quy định, còn recursive chunking tổng quát hơn khi tài liệu không có tiêu đề rõ ràng. Khi so sánh các chiến lược, cần giữ nguyên corpus, embedding, query và top-k để khác biệt kết quả thực sự đến từ cách chunk.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **58 / 60** |
