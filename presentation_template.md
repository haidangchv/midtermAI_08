# (Slide 4:3) Midterm – A* Search
- Thành viên: MSSV, Họ tên, Email, Nhiệm vụ, %
- Task 1: mô hình, 4 goal, 2 heuristic (admissible/consistent), vẽ cây, A* vs BFS
- Task 2: luật Pacman, state, heuristic hợp lệ (không Euclid/Manhattan), Manual+Auto, GUI
- Kết quả: bảng/đồ thị; Ưu/nhược điểm; Bài học; Tổng kết

# Heuristic Overview (A* Midterm)

Mục tiêu: chọn heuristic admissible (và lý tưởng là consistent) để A* tối ưu.
Bài toán: 8-Puzzle (luật swap đặc biệt) & Pacman (food→Exit, map động).
Heuristic dùng:
- HCeilHalf (ceil(H/2)) – 8-Puzzle
- HPDBAdditive (PDB cộng dồn 2 pattern) – 8-Puzzle
- HMax = max(HCeilHalf, HPDB) – 8-Puzzle
- MST-LB trên bản đồ tĩnh – Pacman

# 8-Puzzle – HCeilHalf
Định nghĩa:
- Gọi H = số ô sai vị trí (bỏ ô trống). Đặt h(s) = ceil(H/2).
- Trực giác: 1 nước đi của đề (swap A+B=9 hoặc swap góc chéo) có thể “sửa đúng chỗ” tối đa 2 ô ⇒ cần ≥ ceil(H/2) bước.
- Admissible: Không thể giải xong < ceil(H/2) bước ⇒ cận dưới hợp lệ.
- Consistent (phác thảo): Khi thực hiện 1 bước (cost=1), H giảm không quá 2, nên h(s) - h(s') ≤ ceil(2/2) = 1 ⇒ h(s) ≤ 1 + h(s').
Ưu/nhược: Rẻ, dễ tính; nhưng khá lỏng trên các trạng thái sâu.

# 8-Puzzle – HPDBAdditive (Pattern DB)
Ý tưởng: Tách 8 viên gạch thành hai pattern rời (vd: {1,2,3,4} và {5,6,7,8}).
- Dựng PDB bằng reverse-BFS từ tập 4 goal theo đúng luật đề; lưu chi phí tối ưu theo pattern (projection).
- Heuristic: h_PDB(s) = PDB_1(s) + PDB_2(s) (vì 2 pattern rời ⇒ additive).
- Admissible: Mỗi PDB là cận dưới (thư giãn giữ đúng luật nhưng chỉ “quan tâm” một phần viên gạch). Tổng hai cận dưới vẫn là cận dưới.
- Consistency: Thực tế thường gần/đạt; nếu chỉ chắc admissible: vẫn đủ cho yêu cầu đề.
Ưu/nhược: Mạnh hơn HCeilHalf; tốn dựng PDB (khởi tạo 1 lần, có thể giới hạn max_states).

# 8-Puzzle – HMax (Kết hợp)
Định nghĩa: h_max(s) = max(h_ceil(s), h_pdb(s)).
Tính chất: max của các admissible vẫn admissible; thường mạnh hơn từng cái lẻ.
Thực tế: Nếu PDB chưa phủ đủ key (trả 0 nhiều), HMax vẫn giữ sức mạnh nhờ HCeilHalf.
Khuyến nghị thí nghiệm: So sánh A* với HCeil, PDB, HMax trên cùng bộ case.

# Pacman – MST Lower Bound (tĩnh)
Bài toán: Ăn tất cả food, sau đó tới Exit. Map thật có ma, teleport góc, TTL xuyên tường, xoay 90° mỗi 30 bước.
Heuristic (thư giãn tĩnh):
Tính khoảng cách BFS (trên map tĩnh, bỏ ma/TTL/xoay) giữa {Pacman} ∪ {foods} ∪ {Exit}.
Lấy MST của đồ thị đầy đủ này → h_MST(s).
Admissible: Thư giãn bỏ ràng buộc ⇒ đường đi thật không thể ngắn hơn chi phí MST tĩnh.
Consistency (trực giác): BFS-metric có tam giác; khi dịch chuyển 1 bước, chi phí MST không thể giảm hơn 1 một cách “vô cớ”. Thực nghiệm cho thấy hoạt động ổn định.
Ưu/nhược: Mạnh, dễ cài; chi phí tính có thể cao nếu nhiều food (có thể cache dần BFS).

# Cách đo & trình bày kết quả (gợi ý slide)
Chung cho mọi thí nghiệm:
Mỗi case log: cost, expanded, generated, time_ms.
Biểu đồ: cột hoặc boxplot cho expanded/time_ms; bảng tóm tắt mean/median.

- 8-Puzzle:
So sánh A* (HCeil), A* (PDB), A* (HMax) và BFS.
Kỳ vọng: HMax ít expanded nhất, nhanh hơn; BFS nổ nhánh.

- Pacman:
So sánh A* (MST-LB) vs BFS trên 2–3 layout (ít/many food).
Kỳ vọng: A* ổn định, BFS nhanh “đuối” khi map lớn.

# Kết luận

HCeilHalf: rẻ, ổn định; làm baseline vững chắc.
HPDBAdditive: mạnh; trade-off thời gian dựng PDB.
HMax: “best of both worlds”, khuyên dùng cho 8-Puzzle.
Pacman MST-LB: đáp ứng ràng buộc không dùng Euclid/Manhattan, admissible, hiệu quả thực tế cao.
A* với heuristic phù hợp vượt trội BFS về thời gian/không gian.

HCeilHalf: vẽ 1 state có 5 ô sai vị trí ⇒ ceil(5/2)=3 bước tối thiểu.

PDB: minh hoạ pattern {1,2,3,4}, mũi tên reverse-BFS từ goal; ô tô màu chỉ entries đã “cover”.

MST-LB: vẽ các node {P, food… E}, thêm cạnh = BFS-độ dài, highlight cây MST.