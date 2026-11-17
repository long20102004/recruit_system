---
name: ptit-uml-diagrams
description: Quy tắc vẽ bộ biểu đồ UML cho báo cáo môn Phân tích thiết kế hệ thống thông tin (mẫu PTIT) bằng Visual Paradigm — use case, kịch bản chuẩn/ngoại lệ, trích lớp thực thể, biểu đồ trạng thái, lớp pha phân tích, giao tiếp, thiết kế lớp thực thể, thiết kế CSDL, lớp chi tiết, hoạt động, tuần tự, biểu đồ gói. Dùng khi cần vẽ, viết spec hoặc review bất kỳ biểu đồ nào trong báo cáo thiết kế (kể cả HireLens).
---

# Quy tắc vẽ biểu đồ UML theo mẫu báo cáo PTIT

Rút ra từ báo cáo mẫu "Hệ thống quản lý cửa hàng đồ ăn nhanh – Module 3" (nhóm 15, D22CNPM02). Mẫu đi theo đúng trình tự phân tích → thiết kế; mỗi biểu đồ sau **dùng lại tên** ở biểu đồ trước. Khi áp dụng cho dự án khác (ví dụ HireLens) giữ nguyên **cách làm và ký hiệu**, thay nội dung theo tài liệu + source của dự án đó.

Thứ tự ưu tiên khi mâu thuẫn: yêu cầu trực tiếp của người dùng > `DIAGRAM_RULES.md` (đặc thù dự án) > skill này.

## 0. Quy ước chung

### 0.1. Trình tự và chuỗi truy vết
Mỗi chức năng (use case chính) đi qua đủ chuỗi, và tên phải khớp xuyên suốt:

```
Use case → Kịch bản chuẩn/ngoại lệ → Trích lớp thực thể → Trạng thái
  → Lớp pha phân tích (boundary/entity) → Giao tiếp (kịch bản V2)
  → Thiết kế lớp thực thể → Thiết kế CSDL
  → Lớp chi tiết (giao diện .ts / HTTPClient / RestController / DAO / entity)
  → Hoạt động → Tuần tự (kịch bản V3) → Biểu đồ gói
```

- Mỗi chương trình bày **theo từng chức năng** (1., 2., 3.…), trừ thực thể, CSDL và gói (chung cho cả module).
- Trước mỗi hình có phần **"Bước 1, Bước 2…"** giải thích cách suy ra, kết thúc bằng câu "Ta được biểu đồ …:" rồi đến hình.
- Ngôn ngữ: văn bản tiếng Việt; tên lớp, thuộc tính, phương thức tiếng Anh camelCase, giữ nguyên ở mọi biểu đồ.

### 0.2. Kiểu dáng Visual Paradigm
- Dùng **element gốc trong palette**, màu mặc định của VP (nền xanh nhạt `122,207,245`, viền đen; bảng ERD màu cam mặc định). Không tô màu tự chế.
- Hình xuất ra còn chữ "Powered By Visual Paradigm Community Edition" là bình thường.
- Stereotype biểu tượng (robustness icon): **boundary** (vòng tròn có vạch đứng bên trái), **control** (vòng tròn có mũi tên), **entity** (vòng tròn có gạch dưới), dùng trong **biểu đồ giao tiếp và tuần tự**. Trong biểu đồ lớp thì vẽ hộp lớp thường, không dùng icon.

### 0.2b. Bội số quan hệ (quy định của người dùng, 2026-11-18)
- Giữa các lớp và giữa các bảng **chỉ dùng quan hệ 1-1 hoặc 1-n**; bội số chỉ là `1` hoặc `n`.
- Không dùng `0..1`, `0..n`, `0..*`, `*`, `1..*`. Quy đổi: `0..1` → `1`; mọi bội số "nhiều" → `n`.
- ERD: đầu bảng cha luôn `1`; đầu bảng con `1` (quan hệ 1-1) hoặc nhiều (1-n).

### 0.2c. Góp ý của người dùng (bắt buộc, tổng hợp đến 2026-11-18)
1. **Element gốc + kiểu dáng mặc định:** vẽ bằng đúng element trong palette của Visual Paradigm (Class, Package, Note, Association, Actor, Use Case, Lifeline, DB Table…). Không tô màu, không "giả" hình bằng shape khác.
2. **Tổ chức file:** mỗi loại biểu đồ một package (thư mục `NN_TenLoai/`), **mỗi biểu đồ một file `.vpp` riêng**. Trong file, mọi phần tử nằm trong một Package gốc mang ID biểu đồ.
3. **Không để chữ đè nhau:** nhãn đường nối, bội số, tên phần tử không được chồng lên nhau hay lên hình khác. Cách làm:
   - Các quan hệ song song giữa cùng một cặp lớp/bảng **gộp thành một đường**, nhãn ghi nhiều dòng.
   - Nhãn lặp lại giống nhau trên nhiều đường (ví dụ "logical (khác service)") **bỏ khỏi đường nối**, gom thành một Note chung của hình.
   - Nút rẽ nhánh / gộp (decision, merge, fork, join, choice) **không ghi tên**, chỉ ghi guard trên nhánh ra.
   - Biểu đồ gói **không ghi nhãn trên đường nối**.
   - Rải điểm nối dọc theo cạnh hình để bội số các đường không chồng nhau.
   - Sau khi xuất PNG phải tự xem lại; còn đè chữ thì sửa trước khi bàn giao.
4. **Bội số chỉ `1` hoặc `n`:** quan hệ giữa lớp/bảng chỉ là 1-1 hoặc 1-n (xem 0.2b).
5. **Vẽ theo source khi tài liệu mâu thuẫn:** mã nguồn hiện hành là chuẩn (ví dụ HireLens là microservices dù báo cáo cũ mô tả monolith); ghi điểm lệch vào notes để sửa báo cáo.
6. **Bám sát mẫu PTIT:** đủ 12 loại biểu đồ theo đúng trình tự ở 0.1; trước mỗi hình có "Bước 1, 2…" và câu "Ta được biểu đồ …:".
7. **An toàn với file `.vpp`:** đóng hẳn Visual Paradigm trước khi sửa/render; sao lưu trước khi ghi đè; không lưu từ cửa sổ VP đang mở bản cũ (VP ghi đè khi đóng).

### 0.3. Quy ước đặt tên
| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Lớp biên (phân tích) | `<Tên>View` | `LoginView`, `OrderInfoView` |
| Thuộc tính lớp biên (phân tích) | `in…` ô nhập, `out…` dữ liệu hiển thị, `sub…` nút/submit, `outsub…` danh sách bấm được | `inUsername`, `outOrderCode`, `subApprove`, `outsubFoodList` |
| Trang giao diện (thiết kế) | tên file thật của framework | `Login.ts`, `OrderInfo.ts` (React: `LoginPage.tsx`) |
| Thuộc tính giao diện (thiết kế) | `txt…: input`, `btn…: link/submit/Button`, `tbl…: Table`, `tab…: Tabs`, `…Info: TextField[]`; thuộc tính ẩn ghi riêng | `txtUsername: input`, `tblOrderList: Table`, `e: Employee` |
| Lớp DAO | `<Entity>DAO`, kế thừa lớp `DAO` gốc | `OrderDAO`, `BillDAO` |
| Bảng CSDL | `tbl<TênLớp>` | `tblOrder`, `tblOrderedFood` |
| Khóa ngoại | `id<TênBảngCha>` | `idOrder`, `idCustomer` |
| Lớp trung gian n-n | ghép tên ngữ nghĩa | `OrderedFood`, `OrderPromotion` |

---

## 1. Biểu đồ Use case

### 1.1. Use case tổng quan
**4 bước** (ghi rõ trong báo cáo):
1. **Tên hệ thống**: một System boundary (hình chữ nhật) ghi "Hệ thống … - Module N".
2. **Actor**:
   - Actor trực tiếp, kèm actor cha tổng quát (ví dụ `Nhân viên cửa hàng` hoặc `Thành viên`). Các actor con nối tới cha bằng **Generalization**.
   - Actor gián tiếp (khách hàng, nhân viên giao hàng) đặt ngoài boundary.
3. **Use case**: mỗi chức năng chính của module là một use case.
   - Use case `Đăng nhập` gắn với actor cha.
   - Chức năng con dùng `<<extend>>` kèm **extension points** ghi trong use case gốc (ví dụ "Quản lý thông tin món ăn" có extension point "Tìm kiếm món ăn theo tên").
4. **Mô tả use case**: gạch đầu dòng "Tên: cho phép <actor> <làm gì>".

### 1.2. Use case chi tiết (mỗi chức năng một hình)
1. Sao chép use case và actor liên quan từ biểu đồ tổng quan.
2. **Mỗi giao diện chính là một use case chi tiết** (đăng nhập, xem giao diện chính, xem danh sách, xem chi tiết, hủy…).
3. Xét quan hệ với use case chính:
   - `<<include>>`: bước bắt buộc (đăng nhập, xem giao diện chính, xem danh sách).
   - `<<extend>>`: bước tùy chọn (hủy đơn, liên hệ khách, cập nhật món, phân công lại). **Mũi tên extend đi từ use case mở rộng tới use case gốc**; use case gốc hiện ô *extension points*.
   - Use case con có thể `<<extend>>` tiếp (ví dụ "Nhân viên bán hàng đăng nhập" extend "Đăng nhập" có extension points theo vai trò).
4. Mô tả từng use case chi tiết.

**Element VP:** Use Case Diagram, gồm System, Actor, Use Case (có compartment *extension points*), Association, Include, Extend (nét đứt, mũi tên mở, nhãn `<<Include>>`/`<<Extend>>`), Generalization.

---

## 2. Kịch bản chuẩn và ngoại lệ

Mỗi chức năng một **bảng 2 cột**:

| Dòng | Nội dung |
|---|---|
| Scenario | Tên chức năng |
| Actor | Các actor |
| Pre-condition | Điều kiện trước (tài khoản đúng vai trò, dữ liệu đã có…) |
| Post-condition | Kết quả đạt được |
| Main events | Các bước đánh số 1, 2, 3… xen kẽ **người dùng làm gì**, **hệ thống hiện gì** |
| Exceptions | Đánh số theo bước gốc: `6.1, 6.2…`; nhánh lồng `12.1.1`, `12.2.4.1` |

Quy tắc viết:
- Dùng **dữ liệu cụ thể** (username = a, password = a@123, từ khóa 'gà rán', mã đơn ABC123).
- Khi hệ thống hiện danh sách hoặc chi tiết, chèn **bảng dữ liệu mẫu** (STT, mã, tên, giá…) hoặc danh sách trường.
- Ghi rõ các nút/lựa chọn trên mỗi giao diện ("Lựa chọn duyệt đơn, hủy đơn, Back, liên hệ khách hàng").
- Mỗi ngoại lệ kết thúc bằng việc hệ thống quay về giao diện nào.

---

## 3. Trích lớp thực thể (pha phân tích)

**5 bước:**
1. Mô tả module bằng **một đoạn văn**.
2. & 3. **Trích danh từ và đánh giá:** danh từ thành lớp (kèm thuộc tính trong ngoặc), thành thuộc tính của lớp nào, hoặc bị loại vì chung chung (ví dụ "Hệ thống").
4. & 5. **Xác định quan hệ** giữa các lớp và **bổ sung quan hệ đối tượng**, mỗi quan hệ một câu có lý do:
   - Quan hệ 1-n, n-1, 1-1.
   - n-n thì tạo **lớp trung gian** (association class, nối bằng đường đứt tới đường association).
   - Lớp cha chung (`Member`) với các lớp con kế thừa (`Employee`, `Customer`).
   - Trạng thái đặc biệt tách thành **lớp con kế thừa** (`CancelledOrder` kế thừa `Order`, thêm `reason`).
   - Ghi chú khi một quan hệ n-n *không phải* association class (ví dụ `OrderAssignment`).

**Biểu đồ:** Class Diagram, chỉ có **tên thuộc tính, không ghi kiểu**, không có phương thức. Quan hệ:
- Generalization.
- Aggregation (thoi rỗng) / Composition (thoi đặc) kèm bội số `1`, `n`.
- Association class nét đứt.

---

## 4. Biểu đồ trạng thái

**2 bước** (mỗi chức năng một hình):
1. **Mỗi giao diện chính là một trạng thái** ("Hiện giao diện …", "Hiện thông báo …").
2. **Chuyển trạng thái** viết thành gạch đầu dòng "Tại giao diện X, nếu … thì …".

**Element VP:** State Machine Diagram, gồm Initial, State (bo tròn), Final, Fork/Join (thanh đen) để rẽ nhánh theo kết quả kiểm tra, Transition.
- Nhãn transition dạng `[điều kiện] / hành động`, ví dụ `[Nhập từ khóa và click tìm kiếm] / Tìm danh sách món ăn`. Nhãn dài thì xuống dòng (~34 ký tự/dòng).
- Fork/Join/Choice **không ghi tên** (tránh đè lên nhãn transition).
- Nút quay lại ghi `[Cancel]`, `[Click OK]`, `[Click back]`.

---

## 5. Biểu đồ lớp pha phân tích

**Bước 1 + 2: mỗi giao diện chính đề xuất một lớp biên** (`…View`), liệt kê thuộc tính `in/out/sub`.
- Với mỗi hành động cần xử lý, đề xuất **một hàm** và ghi rõ 4 dòng: tên hàm, **Input**, **Output**, **Lớp chủ thể** (lớp thực thể chứa hàm).
- Ví dụ: `checkLogin()`, Input username, password; Output void; Lớp chủ thể Member.
- Hàm dùng lại thì ghi "đã trình bày ở chức năng 1".

**Biểu đồ:** Class Diagram gộp lớp biên với lớp thực thể của bước 3.
- Lớp biên nối nhau theo luồng điều hướng.
- Lớp biên nối tới lớp thực thể có hàm nó gọi.
- Hàm được đặt vào **lớp thực thể** (`+searchFood()`, `+getOrderListByStatus()`).
- Lớp biên chỉ có thuộc tính.

---

## 6. Biểu đồ giao tiếp (pha phân tích)

1. Viết **"Kịch bản chuẩn V2"**: đánh số liên tục, mỗi bước một câu dạng
   - "Lớp A gọi lớp B (để xử lý)"
   - "Lớp B thực hiện hàm f()"
   - "Lớp B trả kết quả cho lớp A"
   - "Lớp X hiển thị cho <actor>"
   - "<Actor> click/chọn …"
2. Vẽ **Communication Diagram**:
   - Actor; object lớp biên (icon **boundary**), lớp thực thể (icon **entity**), lớp hạ tầng (WebSocket: icon **control**).
   - Message đánh số **khớp 1-1 với kịch bản V2**, nhãn ngắn: `1: login`, `2: call`, `3: checkLogin()`, `4: return`, `9: show`.
   - Hàm tự thực hiện vẽ thành **self-link** trên object.

---

## 7. Thiết kế lớp thực thể

**4 bước:**
1. Thêm `id` cho các lớp **không kế thừa** lớp khác.
2. Bổ sung **kiểu dữ liệu**: `int`, `String`, `DateTime`, `double`.
3. Chuyển association thành **aggregation/composition**; lớp trung gian n-n thành "A là thành phần của Trung gian, Trung gian là thành phần của B".
4. **Bổ sung thuộc tính đối tượng** theo quan hệ thành phần, mỗi dòng ghi:
   - Quan hệ 1-n → lớp n có một thuộc tính kiểu lớp 1 (`OrderedFood` có `food: Food`).
   - Quan hệ n-1 → lớp 1 có `List<…>` (`Order` có `listOrderedFood: List<OrderedFood>`).

**Biểu đồ:** Class Diagram.
- Mọi thuộc tính dạng `-tên : Kiểu` (visibility private).
- Có thuộc tính đối tượng / `List<>`.
- Thoi đặt ở phía "toàn thể", bội số `1`/`n`.
- Giữ generalization.

---

## 8. Thiết kế cơ sở dữ liệu

**5 bước:**
1. **Mỗi lớp thực thể là một bảng `tbl<Lớp>`.** Được tách bảng để tránh dư thừa, ví dụ `OrderAssignment` tách thành `tblOrderApproveAssign`, `tblOrderCancelAssign`, `tblOrderDeliverAssign`.
2. **Thuộc tính không phải đối tượng thành cột**, liệt kê theo từng bảng.
3. **Quan hệ số lượng giữa lớp thành quan hệ giữa bảng** ("1 tblOrder – n tblOrderedFood").
4. **Khóa:**
   - Khóa chính là `id`. Bảng của lớp kế thừa dùng khóa của bảng cha làm PK, đồng thời là FK (`tblEmployee.idMember`).
   - Khóa ngoại `id<Bảng cha>` đặt ở phía n (hoặc phía phụ thuộc trong quan hệ 1-1).
5. **Loại bỏ thuộc tính dư thừa** (trùng lặp, dẫn xuất); nếu không có thì ghi rõ.

**Biểu đồ:** Entity Relationship Diagram của VP.
- Bảng (DB Table) có cột kèm kiểu SQL: `integer(10)`, `varchar(255)`, `timestamp`, `double(10)`.
- Biểu tượng: chìa khóa (PK), chìa khóa có mũi tên (FK, chữ nghiêng), ký hiệu `N` (nullable).
- Quan hệ crow's foot nét đứt, đầu `|` (một) và `<` có `o` (không hoặc nhiều).

---

## 9. Thiết kế biểu đồ lớp chi tiết (mỗi chức năng)

Mở đầu: nêu **framework frontend/backend** (mẫu dùng Angular TS + Spring Boot JPA). Chia **4 tầng**, mỗi tầng một mục a–d.

**a. Tầng giao diện:**
- Mỗi trang gồm:
  - Tên file `.ts` và **ảnh chụp giao diện thật**.
  - **Thuộc tính tường minh** (`txt…: input`, `btn…: link`…) và **thuộc tính ẩn** (`e: Employee (lấy từ session)`, `order: Order`).
  - Có gọi backend không, để làm gì.
  - Điều hướng sang trang nào khi bấm từng nút.
- Cuối mục là hình **"Quan hệ giữa các giao diện"**: ghép ảnh chụp các trang, nối bằng mũi tên điều hướng.

**b. Tầng thao tác CSDL:**
- Lớp `DAO` gốc có `+em: EntityManager`, `+DAO()`, ghi chú "kết nối do Spring Boot tự cấu hình".
- Mỗi `XxxDAO` kế thừa `DAO`. Từng phương thức ghi đủ tên, **Input**, **Output** (ví dụ `getOrderInfo(orderId: int): Order`).
- Phương thức dùng lại thì ghi "(giống chức năng trên)".

**c. Tầng thực thể:** liệt kê các lớp thực thể dùng trong chức năng; có thể ghi "toàn bộ, trừ lớp Store".

**d. Các lớp phụ trợ:**
- `HTTPClient` có `+fetch()`, gọi API từ frontend.
- `RestController` có `+requestMapping()`, điều hướng request.
- Hạ tầng thêm nếu cần (`WebSocket` có `sendMessage()`).

**Biểu đồ:** Class Diagram, xếp từ trên xuống:
1. Các trang `.ts` (hàng trên).
2. `HTTPClient`.
3. `RestController`.
4. Các `DAO` (kế thừa `DAO`).
5. Lớp thực thể (giữ quan hệ của mục 7).

Các trang nối tới `HTTPClient`, `RestController` nối tới các DAO, DAO nối tới entity nó thao tác. Thuộc tính trang ghi kiểu (`-txtUsername : input`).

---

## 10. Thiết kế biểu đồ hoạt động (mỗi chức năng)

- **Bước 1: mỗi lớp giao diện đề xuất một activity.** Vẽ thành vùng chứa (Activity / Structured activity) mang tên file `Login.ts`.
- **Bước 2: mỗi hoạt động trong giao diện là một action**, nối tuần tự. Các action chuẩn hóa:
  - "Hiện giao diện"
  - "Lấy từ form: …"
  - "Lưu vào session: …" / "Lấy từ session: …"
  - "Gọi hàm f()"
  - "Thông báo …"
- Liệt kê action theo từng `.ts` trong văn bản trước hình.
- Có thêm vùng cho `HTTPClient` (`fetch()`), `RestController` (`requestMapping()`), từng `XxxDAO` (mỗi phương thức một action).
- Mỗi action "Gọi hàm f()" nối **hai chiều** qua `fetch()` → `requestMapping()` → action DAO tương ứng.

**Element VP:** Activity Diagram, gồm:
- Initial ("Bắt đầu"), Activity Final ("Kết thúc").
- Action (bo tròn), Decision (hình thoi).
- Control flow có guard `[Thành công]`, `[Thất bại]`, `[Click OK]`, `[Không tìm thấy]`.
- Decision/Merge **không ghi tên**, điều kiện chỉ nằm trên guard của nhánh ra.

---

## 11. Thiết kế biểu đồ tuần tự (mỗi chức năng)

1. Viết **"Kịch bản chuẩn V3"**, chi tiết hơn V2, đi đủ đường:
   - **Trang .ts → HTTPClient** (`fetch()`) **→ RestController** (`requestMapping()`) **→ XxxDAO** (hàm nghiệp vụ).
   - **→ Entity** ("thực hiện hàm khởi tạo, setter"). Entity lồng nhau gọi tiếp: Order → OrderedFood → Food.
   - **Trả kết quả ngược** từng tầng, rồi trang hiện kết quả.
   - Các bước session: "lưu vào session: orderId" / "lấy từ session: orderId".
2. Vẽ **Sequence Diagram (Interaction Diagram)**:
   - **Lifeline trái → phải:**
     1. Actor.
     2. Các trang `.ts` (icon **boundary**).
     3. `HTTPClient`, `RestController`, các `DAO`, `WebSocket` (icon **control**).
     4. Các entity (icon **entity**).
   - **Message đánh số khớp 1-1 với V3:**
     - Lời gọi giữa lifeline có nhãn `call`.
     - Hàm thực thi là **self-message** `fetch()`, `requestMapping()`, `getOrderInfo()`, `Order(), setter()`.
     - Trả về nét đứt `return`.
     - Hiển thị cho actor `show`.
     - Thao tác của actor ghi bằng lời (`1: login`, `16: choose an order`).
   - Activation bar trên mọi lifeline đang xử lý.
   - Luồng song song hoặc chờ dùng **combined fragment** (`par`, `alt`, `opt`, `loop`) có guard.

---

## 12. Thiết kế biểu đồ gói (chung module)

- Gói `View` chứa các trang, chia **gói con theo actor** (`Seller`, `Manager`, `DeliveryEmployee`). Trang dùng chung (`Login.ts`) đặt ở gói cha.
- Lớp phụ trợ mỗi loại một gói: `FetchAPI` (`HTTPClient`), `Controller` (`RestController`), `WebSocket`.
- `DAO` chứa mọi DAO, giữ quan hệ kế thừa. `Model` chứa mọi entity, giữ quan hệ của mục 7.
- Vẽ bằng Package lồng nhau, **lớp đặt bên trong package** (chỉ hiện tên lớp), giữ các đường nối giữa lớp.
- **Không ghi nhãn trên đường nối** của biểu đồ gói (chi tiết lời gọi xem biểu đồ lớp chi tiết); mỗi gói con phải có lớp (không để gói rỗng).

---

## 13. Áp dụng cho pipeline vẽ tự động trong dự án này

- Spec, render, thư mục và quy trình an toàn với `.vpp`: xem `CLAUDE.md` và `DIAGRAM_RULES.md`. Mỗi biểu đồ một file `.vpp`.
- Ánh xạ sang `type` của renderer `hirelens.tools`:

| Biểu đồ | `type` | Hỗ trợ renderer |
|---|---|---|
| Use case | `usecase` | có (`UseCaseRenderer`) |
| Trạng thái | `state` | có (`StateRenderer`) |
| Giao tiếp | `communication` | có (`CommunicationRenderer`; nhãn message ghi trên đường link dạng `→ 1: login`) |
| Trích lớp thực thể, lớp phân tích, thiết kế thực thể, lớp chi tiết | `class` | có (cần `stereotype` boundary/control/entity khi vẽ icon ở giao tiếp/tuần tự) |
| Thiết kế CSDL | `erd` | có |
| Hoạt động (vùng theo trang `.ts`) | `activity` | có; vùng `.ts` nên dùng partition hoặc structured activity |
| Tuần tự | `sequence` | có (lifeline có stereotype để hiện icon boundary/control/entity) |
| Gói | `package` | có |

- **Với dự án không phải Angular/DAO** (ví dụ HireLens: React + Spring Data JPA, microservices), giữ **khung tầng** của mẫu và ánh xạ sang tên thật trong source:
  - Trang `.ts` → `XxxPage.tsx`.
  - `HTTPClient` → `api/client.ts`.
  - `RestController` → `XxxController`.
  - `DAO` → `XxxRepository`/`XxxService`.
  - Không tự tạo lớp không có trong code. Ghi chú sự khác biệt so với mẫu ngay dưới hình.

## 14. Checklist trước khi bàn giao

- [ ] Mỗi chức năng có đủ: use case chi tiết, kịch bản, trạng thái, lớp phân tích, giao tiếp, lớp chi tiết, hoạt động, tuần tự.
- [ ] Phần chung có đủ: use case tổng quan, trích lớp thực thể, thiết kế thực thể, CSDL, gói.
- [ ] Trước mỗi hình có các bước suy ra và câu "Ta được biểu đồ …:".
- [ ] Số bước kịch bản V2 khớp message giao tiếp; V3 khớp message tuần tự.
- [ ] Tên lớp, hàm, thuộc tính khớp xuyên suốt: phân tích → thiết kế → hoạt động → tuần tự → gói.
- [ ] Mọi hàm có Input/Output/Lớp chủ thể (phân tích) hoặc chữ ký đầy đủ (DAO).
- [ ] Bảng CSDL đủ PK/FK, kiểu SQL; quan hệ crow's foot đúng bội số.
- [ ] Element gốc của VP, màu mặc định, xuất PNG và tự xem lại.
- [ ] Mỗi loại biểu đồ một thư mục, mỗi biểu đồ một file `.vpp`.
- [ ] Không còn chữ đè: nhãn đường nối, bội số, tên phần tử, nhãn guard.
- [ ] Bội số chỉ `1`/`n`; quan hệ song song đã gộp; nhãn lặp lại đã chuyển vào Note.
- [ ] Nút rẽ nhánh không ghi tên; biểu đồ gói không có nhãn đường nối; mũi tên extend đúng chiều.
