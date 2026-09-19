# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** G21  
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân của mỗi thành viên được trình bày trong `REPORT_CANHAN.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề và lý do chọn

**Chủ đề:** Học phí và quy định thu nộp học phí của các trường đại học tại Việt Nam.

**Lý do chọn:**

> Học phí là nhu cầu tra cứu thực tế của sinh viên và có nhiều dạng câu hỏi như mức thu, công thức tính, thời hạn, phương thức thanh toán và xử lý khi nộp muộn. Các trường có quy định khác nhau nhưng dùng nhiều từ vựng giống nhau, vì vậy chủ đề phù hợp để kiểm tra semantic retrieval, chunking theo cấu trúc và metadata filter.

### Data Inventory

| # | Tên tài liệu | Nguồn | Ngày lấy / phiên bản | Số ký tự | Metadata chính |
|---|---|---|---|---:|---|
| 1 | Quy định về thu nộp học phí đối với sinh viên FTU | https://khoadaotaotructuyen.ftu.edu.vn/van-ban-bieu-mau/quy-dinh-ve-thu-nop-hoc-phi-doi-voi-sinh-vien/ | 2026-09-19 / `not-stated` | 3.047 | `audience=student`, `department=finance`, `category=tuition`, `language=vi` |
| 2 | Quy định về việc thu học phí đào tạo các bậc học của Trường ĐHKHTN | https://bio.hus.vnu.edu.vn/quy-dinh-ve-viec-thu-hoc-phi-dao-tao-cac-bac-hoc-cua-truong-dhkhtn/ | 2026-09-19 / `not-stated` | 3.164 | `audience=all`, `department=finance`, `category=tuition`, `language=vi` |
| 3 | Thay đổi lịch thu tiền học phí Đợt 1, học kỳ I năm học 2026–2027 của VNUA | https://vnua.edu.vn/thong-bao/thay-doi-lich-thu-tien-hoc-phi-dot-1-hoc-ki-i-nam-hoc-2026-2027-doi-voi-sinh-vien-58812 | 2026-09-19 / `2026-07-18` | 3.383 | `audience=student`, `department=finance`, `category=tuition`, `language=vi` |

**Tình trạng corpus:** Hiện có 3 tài liệu đã làm sạch và `sources.csv` khớp 1-1. Corpus đã có hai giá trị `audience` là `student` và `all`, nhưng chưa đạt yêu cầu 5–10 tài liệu của Checkpoint 2. Nhóm cần bổ sung tối thiểu 2 tài liệu trước khi nộp bản cuối.

### Data governance checklist

- [x] Chỉ sử dụng nội dung từ các trang công khai và ghi lại URL nguồn.
- [x] Không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi file có `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version` và `audience`.
- [x] Nội dung đã được làm sạch menu, footer và phần tin tức không liên quan.
- [x] `sources.csv` ánh xạ 1-1 với ba file Markdown hiện tại.
- [ ] Corpus có đủ 5–10 tài liệu theo yêu cầu.

### Metadata Schema

| Trường | Kiểu | Ví dụ | Vai trò trong retrieval |
|---|---|---|---|
| `doc_id` | string | `vnua-thong-bao-thu-hoc-phi-2026` | Định danh tài liệu gốc, hỗ trợ truy vết và xóa toàn bộ chunk của một tài liệu |
| `title` | string | `Quy định về thu nộp học phí...` | Giúp nhận biết kết quả trong top-k |
| `source_url` | string | URL trang nguồn | Kiểm chứng nội dung và provenance |
| `retrieved_at` | date | `2026-09-19` | Theo dõi thời điểm thu thập |
| `document_version` | string | `2026-07-18` / `not-stated` | Phân biệt phiên bản và tránh tự bịa số hiệu |
| `audience` | enum | `student` / `all` | Lọc đúng đối tượng sử dụng quy định |
| `department` | string | `finance` | Lọc theo đơn vị hoặc lĩnh vực quản lý |
| `category` | string | `tuition` | Gom nhóm tài liệu theo nghiệp vụ |
| `language` | string | `vi` | Hỗ trợ corpus đa ngôn ngữ |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích baseline

Nhóm chạy `ChunkingStrategyComparator().compare()` trên phần thân của ba tài liệu, không tính YAML frontmatter.

| Tài liệu | Fixed-size: số chunk / TB ký tự | Sentence: số chunk / TB ký tự | Recursive: số chunk / TB ký tự |
|---|---:|---:|---:|
| FTU | 6 / 447,8 | 8 / 334,2 | 7 / 382,4 |
| HUS | 6 / 467,2 | 9 / 309,3 | 7 / 398,9 |
| VNUA | 6 / 495,2 | 9 / 328,1 | 7 / 422,7 |
| **Tổng** | **18 chunks** | **26 chunks** | **21 chunks** |

**Nhận xét:**

- Fixed-size tạo ít chunk nhất và độ dài khá đồng đều, nhưng có thể cắt ngang câu hoặc mục.
- Sentence tạo nhiều chunk nhất; các đoạn dễ đọc nhưng có nguy cơ quá nhỏ và mất liên kết giữa tiêu đề với nội dung.
- Recursive cân bằng số lượng và độ dài, ưu tiên ranh giới đoạn/câu nhưng không hiểu trực tiếp cấu trúc heading.

### Chiến lược của từng thành viên

| Thành viên | Chiến lược | Cấu hình | Trạng thái bằng chứng |
|---|---|---|---|
| Phùng Gia Khánh | `HeadingChunker` | `chunk_size=500`, section dài dùng `RecursiveChunker`; gắn lại heading vào từng mảnh con | Đã chạy bằng Gemini, 26 chunks, điểm content-level 6/10 |
| Thành viên 2 — nhóm xác nhận tên | `RecursiveChunker` | Đề xuất `chunk_size=500` | Chưa nhận `ket_qua_benchmark.txt` |
| Thành viên 3 — nhóm xác nhận tên | `FixedSizeChunker` | Đề xuất `chunk_size=500`, `overlap=50` | Chưa nhận `ket_qua_benchmark.txt` |

### HeadingChunker của Phùng Gia Khánh

Văn bản quy định thường được biên soạn theo các mục `##`. `HeadingChunker` tách trước mỗi heading để một chunk đại diện cho một đơn vị ngữ nghĩa. Nếu section dài hơn giới hạn, nội dung được chia tiếp bằng recursive chunking và tiêu đề được gắn lại vào từng chunk con để không mất ngữ cảnh.

```python
class HeadingChunker:
    def __init__(self, chunk_size=500):
        self.chunk_size = chunk_size
        self.fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text):
        sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
        # Giữ nguyên section ngắn; section dài được recursive split
        # và heading được gắn lại vào từng mảnh con.
```

### So sánh giữa các thành viên

| Chiến lược | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|---|---:|---|---|
| Heading — Phùng Gia Khánh | 6 | Giữ cấu trúc mục; chunk dễ đọc và truy vết | Các section cùng tài liệu có thể chiếm hết top-k; không có overlap giữa các mục |
| Recursive | Chưa có log | Tổng quát, giữ ranh giới đoạn/câu khá tốt | Có thể tách heading khỏi nội dung nếu cấu trúc phức tạp |
| Fixed-size | Chưa có log | Đơn giản, độ dài ổn định, overlap bảo vệ ranh giới | Có thể cắt ngang đơn vị ngữ nghĩa |

**Kết luận hiện tại:**

> HeadingChunker phù hợp về mặt cấu trúc với corpus quy định, nhưng chưa thể kết luận là chiến lược thắng vì nhóm chưa có log benchmark của Recursive và Fixed-size trên cùng năm câu hỏi. Để so sánh công bằng, cả ba thành viên phải giữ nguyên corpus, Gemini Embedding, top-k và bộ query; chỉ thay dòng chọn chunker.

---

## 3. Câu hỏi đánh giá và chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Bộ 5 câu hỏi và gold answer

| # | Query | Gold answer | Tài liệu chứa đáp án |
|---|---|---|---|
| 1 | Theo quy định FTU, hạn nộp học phí học kỳ I và học kỳ II là khi nào? | Học kỳ I chậm nhất ngày 30/11; học kỳ II chậm nhất ngày 31/5 hằng năm. | `ftu-quy-dinh-thu-nop-hoc-phi.md` |
| 2 | HUS tính học phí môn học của chương trình đào tạo chuẩn theo công thức nào? | 165.000 đồng/tín chỉ × số tín chỉ × hệ số môn học. | `hus-quy-dinh-thu-hoc-phi.md` |
| 3 | Sinh viên VNUA phải đáp ứng điều kiện gì trước khi thanh toán học phí? | Cập nhật thông tin Căn cước công dân trong hồ sơ lý lịch trên hệ thống quản lý đào tạo. | `vnua-thong-bao-thu-hoc-phi-2026.md` |
| 4 | Nếu sinh viên VNUA chưa nộp đủ học phí Đợt 1 đúng hạn thì bị xử lý thế nào? | Không có tên trong danh sách tham dự học phần và bị hủy các học phần Block 1 bắt đầu trước ngày 5/10/2026. | `vnua-thong-bao-thu-hoc-phi-2026.md` |
| 5 | Học phí được thu vào thời điểm nào? | Với tài liệu dành cho sinh viên: FTU quy định hạn học kỳ I là 30/11; VNUA thu Đợt 1 từ 20/7/2026 đến 10/8/2026. | FTU và VNUA; dùng `audience=student` |

### Kết quả HeadingChunker với Gemini Embedding

| # | Content-level rank | Điểm | Đánh giá |
|---|---:|---:|---|
| 1 | 1 | 2/2 | Chunk top-1 chứa đủ hai thời hạn FTU |
| 2 | 1 | 2/2 | Chunk top-1 chứa đúng công thức HUS |
| 3 | 2 | 1/2 | Top-1 cùng chủ đề nhưng sai ý; chunk chứa điều kiện CCCD ở hạng 2 |
| 4 | 2 | 1/2 | Top-1 nói về miễn giảm; chunk chứa cách xử lý ở hạng 2 |
| 5 | Không có chunk chứa đủ marker | 0/2 | Top-3 chỉ có FTU, thiếu lịch VNUA |
| **Tổng** |  | **6/10** | **4/5 câu có chunk trả lời được trong top-3** |

### A/B metadata filter ở câu 5

**Không filter:**

1. FTU — giới thiệu mục thời hạn nộp học phí.
2. HUS — người học nước ngoài nộp học phí theo năm học.
3. FTU — hạn 30/11 và 31/5.

**Có `metadata_filter={"audience": "student"}`:**

1. FTU — giới thiệu mục thời hạn nộp học phí.
2. FTU — hạn 30/11 và 31/5.
3. FTU — hình thức thu nộp học phí.

**Kết luận A/B:** `Top-3 changed: True`. Filter loại được tài liệu HUS có `audience=all`, nhờ đó tăng precision theo đối tượng sinh viên. Tuy nhiên, ba vị trí lại bị các chunk FTU chiếm hết nên lịch VNUA không xuất hiện. Filter giúp giảm nhiễu nhưng không tự bảo đảm recall hoặc sự đa dạng nguồn.

### Failure case

> **Câu lỗi:** Q5 — “Học phí được thu vào thời điểm nào?”  
> **Biểu hiện:** Gold answer cần cả mốc FTU và VNUA, nhưng top-3 sau filter chỉ chứa FTU nên thiếu `20/7/2026`.  
> **Nguyên nhân:** Nhiều section FTU cùng gần với query và chiếm cả ba vị trí; cosine similarity ưu tiên độ gần chủ đề chứ không bảo đảm bao phủ nhiều tài liệu.  
> **Đề xuất:** tăng `top_k`, giới hạn số chunk trên mỗi `doc_id`, áp dụng MMR/diversity reranking hoặc tách câu hỏi thành từng trường nếu mục tiêu không yêu cầu tổng hợp đa nguồn.

### Lưu ý về tính công bằng của benchmark

Q1–Q4 trong lần chạy hiện tại có filter theo `doc_id`. Cách này hữu ích để kiểm tra chunk nào tốt nhất bên trong đúng tài liệu, nhưng làm retrieval toàn corpus dễ hơn và có thể thổi phồng điểm. Bản benchmark cuối nên chạy Q1–Q4 với `Filter: None`; chỉ Q5 dùng `audience=student` để đo đúng khả năng truy xuất giữa các tài liệu.

---

## 4. Thuyết trình và bài học nhóm — Nhóm (5 điểm)

### Nội dung demo 6–8 phút

1. **Chủ đề và corpus (1 phút):** giới thiệu ba nguồn FTU, HUS, VNUA; metadata và quá trình làm sạch.
2. **Ba chiến lược (2 phút):** Fixed-size, Recursive và HeadingChunker; mỗi thành viên trình bày phần của mình.
3. **So sánh (2–3 phút):** số chunk, độ dài trung bình và điểm benchmark trên cùng cấu hình.
4. **Demo trực tiếp (1–2 phút):** chạy một câu trả lời đúng và Q5 để cho thấy tác động của metadata filter cùng failure case.

### Insights chính

- Làm sạch corpus quan trọng không kém chọn embedding; menu và footer có thể chiếm top-k dù không chứa đáp án.
- Chunk đúng tài liệu chưa chắc chứa đúng câu trả lời, vì vậy phải chấm ở content level.
- HeadingChunker giữ tốt cấu trúc văn bản quy định, nhưng nhiều section cùng tài liệu có thể chiếm toàn bộ top-k.
- Metadata filter tăng precision nhưng có thể làm giảm recall nếu metadata quá cứng hoặc corpus chưa được tách đúng đối tượng.
- Gemini Embedding thể hiện ngữ nghĩa tốt hơn MockEmbedder; MockEmbedder chỉ phù hợp cho unit test vì vector được sinh từ hash và không hiểu nội dung.

### Nếu làm lại

> Nhóm sẽ bổ sung corpus lên tối thiểu 5 tài liệu, tách tài liệu theo `audience` khi một trang chứa nhiều đối tượng, và thiết kế query filter sao cho có hai tài liệu cùng chủ đề nhưng khác đáp án. Về retrieval, nhóm sẽ thử giới hạn số chunk trên mỗi `doc_id` hoặc dùng diversity reranking để tránh một tài liệu chiếm toàn bộ top-k. Tất cả thành viên sẽ dùng chung corpus, Gemini Embedding, query và top-k để kết quả so sánh có ý nghĩa.

---

## Tự đánh giá phần nhóm

| Tiêu chí | Điểm tự đánh giá hiện tại | Cơ sở |
|---|---:|---|
| Lựa chọn tài liệu | 6/10 | Metadata và provenance rõ, nhưng mới có 3/5 tài liệu tối thiểu |
| Thiết kế chiến lược | 9/15 | Có baseline và HeadingChunker; thiếu log hai chiến lược còn lại |
| Chất lượng truy xuất | 7/10 | Có 5 query, content-level scoring, A/B và failure case; benchmark hiện đạt 6/10 |
| Thuyết trình | 4/5 | Đã có kịch bản và demo chạy được |
| **Tổng** | **26/40** | **Cần bổ sung corpus và kết quả các thành viên trước bản nộp cuối** |

---

## Việc nhóm cần xác nhận trước khi nộp

- [ ] Điền đúng họ tên Thành viên 2 và Thành viên 3.
- [ ] Bổ sung ít nhất 2 tài liệu để corpus đạt 5–10 file và cập nhật `sources.csv`.
- [ ] Thu `ket_qua_benchmark.txt` của RecursiveChunker và FixedSizeChunker.
- [ ] Hoàn thiện bảng so sánh điểm giữa ba thành viên.
- [ ] Chạy Q1–Q4 không dùng `doc_id` filter và lưu output cuối.
- [ ] Chạy `pytest tests/ -v` và xác nhận 42/42 tests passed trước khi push.
