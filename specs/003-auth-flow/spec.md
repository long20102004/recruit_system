# Feature Specification: Hoàn thiện luồng xác thực

**Feature Branch**: `hocnv/auth-flow` (spec dir `003-auth-flow`)
**Created**: 2026-11-25
**Status**: Draft
**Input**: User description: "Hoàn thiện luồng auth gồm đăng ký, đăng nhập, quên mật khẩu, khoá tài khoản; luồng khoá tài khoản tích hợp thêm Redis." Đã chốt với người dùng: khoá gồm cả tự khoá khi sai mật khẩu nhiều lần và admin khoá; quên mật khẩu gửi link qua email; đăng ký có xác thực email.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đăng ký có xác thực email (Priority: P1)

Người dùng mới đăng ký bằng email và mật khẩu. Hệ thống gửi email chứa link xác thực. Tài khoản chỉ đăng nhập được sau khi bấm link. Bấm link xong, người dùng được đăng nhập luôn và chuyển sang bước chọn vai trò như hiện nay.

**Why this priority**: Là cửa vào của mọi người dùng mới; chặn tài khoản rác và đảm bảo email dùng được cho quên mật khẩu.

**Independent Test**: Đăng ký một email mới → mở hộp thư dev → bấm link → vào màn chọn vai trò.

**Acceptance Scenarios**:

1. **Given** email chưa đăng ký, **When** người dùng đăng ký với mật khẩu hợp lệ, **Then** tài khoản được tạo ở trạng thái chưa xác thực, một email xác thực được gửi, và màn hình báo "kiểm tra email" (không đăng nhập ngay).
2. **Given** tài khoản chưa xác thực, **When** người dùng bấm link trong email trước khi link hết hạn, **Then** tài khoản được đánh dấu đã xác thực, người dùng được đăng nhập và chuyển tới màn chọn vai trò.
3. **Given** tài khoản chưa xác thực, **When** người dùng đăng nhập đúng mật khẩu, **Then** đăng nhập bị từ chối với thông báo "email chưa xác thực" và có nút gửi lại email.
4. **Given** link đã dùng hoặc đã hết hạn, **When** người dùng mở link, **Then** hệ thống báo link không hợp lệ và cho phép gửi lại email xác thực.
5. **Given** email đã đăng ký, **When** đăng ký lại, **Then** bị từ chối với thông báo email đã được đăng ký (giữ hành vi hiện tại).

---

### User Story 2 - Đăng nhập an toàn, tự khoá tạm khi sai nhiều lần (Priority: P1)

Người dùng đăng nhập bằng email và mật khẩu. Nếu nhập sai mật khẩu liên tiếp nhiều lần, tài khoản (theo email) bị khoá tạm một khoảng thời gian; trong thời gian đó kể cả nhập đúng cũng không vào được. Đăng nhập thành công thì bộ đếm sai được xoá.

**Why this priority**: Chống dò mật khẩu là yêu cầu bảo mật cơ bản của luồng đăng nhập.

**Independent Test**: Nhập sai mật khẩu 5 lần → lần thứ 6 (dù đúng) bị báo khoá tạm kèm thời gian còn lại → chờ hết thời gian → đăng nhập đúng thành công.

**Acceptance Scenarios**:

1. **Given** tài khoản hợp lệ, **When** đăng nhập đúng, **Then** nhận phiên đăng nhập như hiện nay và bộ đếm sai về 0.
2. **Given** đã sai 4 lần trong cửa sổ đếm, **When** sai lần thứ 5, **Then** email đó bị khoá tạm 15 phút.
3. **Given** email đang bị khoá tạm, **When** đăng nhập (đúng hay sai), **Then** bị từ chối với thông báo khoá tạm và số phút còn lại; lần thử này không gia hạn khoá.
4. **Given** email không tồn tại, **When** đăng nhập sai nhiều lần, **Then** phản hồi giống hệt email có tồn tại (không lộ email nào đã đăng ký).
5. **Given** tài khoản bị admin khoá, **When** đăng nhập đúng mật khẩu, **Then** bị từ chối với thông báo tài khoản đã bị khoá (không phải lỗi hệ thống như hiện nay).

---

### User Story 3 - Quên mật khẩu qua link email (Priority: P2)

Người dùng quên mật khẩu nhập email; nếu email thuộc một tài khoản dùng được, hệ thống gửi link đặt lại mật khẩu dùng một lần, có hạn. Đặt mật khẩu mới xong, mọi phiên đăng nhập cũ bị vô hiệu và khoá tạm do sai mật khẩu (nếu có) được gỡ.

**Why this priority**: Cần thiết cho người dùng thật nhưng không chặn luồng chính.

**Independent Test**: Gửi yêu cầu quên mật khẩu → mở email → đặt mật khẩu mới → đăng nhập bằng mật khẩu mới thành công, mật khẩu cũ thất bại, token phiên cũ không còn dùng được.

**Acceptance Scenarios**:

1. **Given** bất kỳ email nào, **When** gửi yêu cầu quên mật khẩu, **Then** màn hình luôn hiện cùng một thông báo "nếu email tồn tại, bạn sẽ nhận được link" (không lộ email có tồn tại hay không).
2. **Given** email thuộc tài khoản không bị admin khoá, **When** gửi yêu cầu, **Then** một email chứa link đặt lại mật khẩu có hạn 30 phút được gửi.
3. **Given** link còn hạn, **When** người dùng đặt mật khẩu mới hợp lệ, **Then** mật khẩu được đổi, link hết hiệu lực, các phiên đăng nhập cũ bị vô hiệu, khoá tạm được gỡ, tài khoản chưa xác thực email được coi là đã xác thực.
4. **Given** link đã dùng hoặc hết hạn, **When** đặt mật khẩu, **Then** bị từ chối và gợi ý gửi lại yêu cầu.
5. **Given** vừa gửi yêu cầu cho một email, **When** gửi lại trong vòng 60 giây, **Then** không gửi thêm email (vẫn hiện cùng thông báo).

---

### User Story 4 - Admin khoá / mở khoá tài khoản, có hiệu lực ngay trên mọi service (Priority: P2)

Admin tìm người dùng và khoá tài khoản kèm lý do, hoặc mở khoá. Tài khoản bị khoá không đăng nhập được và mọi phiên đang dùng bị từ chối ngay ở tất cả service. Thông tin trạng thái người dùng được các service đọc qua bộ nhớ đệm dùng chung (Redis) để không phải hỏi identity-service ở mỗi request, và bộ nhớ đệm được làm mới ngay khi trạng thái đổi.

**Why this priority**: Yêu cầu quản trị; phụ thuộc có tài khoản admin (đã có từ seed).

**Independent Test**: Người dùng A đang đăng nhập và gọi API của recruitment-service → admin khoá A → request tiếp theo của A ở bất kỳ service nào bị từ chối; A đăng nhập lại bị báo đã khoá → admin mở khoá → A đăng nhập lại được.

**Acceptance Scenarios**:

1. **Given** admin đã đăng nhập, **When** xem danh sách người dùng có tìm theo email/tên và lọc trạng thái, **Then** thấy danh sách phân trang gồm id, họ tên, email, vai trò, trạng thái, đã xác thực email hay chưa.
2. **Given** người dùng đang hoạt động, **When** admin khoá kèm lý do, **Then** trạng thái thành "bị khoá", lý do được lưu, và request kế tiếp của người đó ở mọi service bị từ chối.
3. **Given** người dùng bị khoá, **When** admin mở khoá, **Then** người dùng đăng nhập lại được; các token đã cấp trước khi khoá vẫn không dùng lại được.
4. **Given** admin, **When** cố khoá chính mình hoặc một admin khác, **Then** bị từ chối.
5. **Given** người dùng không phải admin, **When** gọi các chức năng quản trị này, **Then** bị từ chối truy cập.

### Edge Cases

- Redis không truy cập được: đăng nhập vẫn hoạt động (bỏ qua đếm sai, ghi log cảnh báo); xác thực email, quên mật khẩu trả lỗi "tạm thời không khả dụng"; các service đọc trạng thái người dùng trực tiếp từ identity-service thay cho bộ nhớ đệm.
- Gửi email thất bại khi đăng ký: tài khoản vẫn được tạo, người dùng dùng "gửi lại email xác thực". Khi quên mật khẩu: vẫn hiện thông báo chung, lỗi ghi log (không lộ cho người dùng).
- Gửi lại email xác thực cho email đã xác thực hoặc không tồn tại: hiện thông báo chung, không gửi.
- Link xác thực/đặt lại bị dùng hai lần song song: chỉ một lần thành công.
- Tài khoản bị admin khoá yêu cầu quên mật khẩu: không gửi email, thông báo chung.
- Tài khoản bị admin khoá được mở khoá: khoá tạm do sai mật khẩu (nếu còn) vẫn tính riêng.
- Email nhập có chữ hoa/khoảng trắng: chuẩn hoá chữ thường, cắt khoảng trắng ở mọi luồng (đếm sai, quên mật khẩu, đăng ký).
- Tài khoản seed và tài khoản đã tồn tại trước khi có tính năng: coi là đã xác thực email.

## Requirements *(mandatory)*

### Functional Requirements

**Đăng ký và xác thực email**
- **FR-001**: Hệ thống MUST tạo tài khoản ở trạng thái chưa xác thực email khi đăng ký, và MUST NOT cấp phiên đăng nhập ngay lúc đăng ký.
- **FR-002**: Hệ thống MUST gửi email chứa link xác thực dùng một lần, hết hạn sau 24 giờ.
- **FR-003**: Khi link xác thực hợp lệ được dùng, hệ thống MUST đánh dấu tài khoản đã xác thực, vô hiệu link và cấp phiên đăng nhập.
- **FR-004**: Người dùng MUST gửi lại được email xác thực; giữa hai lần gửi cho cùng email tối thiểu 60 giây; phản hồi không lộ email có tồn tại hay đã xác thực.
- **FR-005**: Mật khẩu MUST dài 8–100 ký tự, có ít nhất một chữ cái và một chữ số (áp dụng cho đăng ký và đặt lại mật khẩu).

**Đăng nhập và khoá tạm**
- **FR-006**: Hệ thống MUST đếm số lần đăng nhập sai theo email (đã chuẩn hoá) trong cửa sổ 15 phút; đạt 5 lần thì khoá tạm email đó 15 phút.
- **FR-007**: Trong thời gian khoá tạm, hệ thống MUST từ chối mọi lần đăng nhập của email đó (kể cả đúng mật khẩu), trả thông báo kèm thời gian còn lại, và MUST NOT gia hạn khoá do các lần thử này.
- **FR-008**: Đăng nhập thành công MUST xoá bộ đếm sai của email đó.
- **FR-009**: Phản hồi đăng nhập sai MUST giống nhau cho email tồn tại và không tồn tại.
- **FR-010**: Đăng nhập tài khoản chưa xác thực email MUST bị từ chối bằng một mã lỗi riêng để giao diện đưa ra lựa chọn gửi lại email. Thông báo này chỉ trả về khi mật khẩu đúng.
- **FR-011**: Đăng nhập tài khoản bị admin khoá MUST bị từ chối bằng mã lỗi riêng "tài khoản đã bị khoá" (thay cho lỗi 500 hiện tại). Thông báo này chỉ trả về khi mật khẩu đúng.

**Quên mật khẩu**
- **FR-012**: Yêu cầu quên mật khẩu MUST luôn trả cùng một phản hồi thành công bất kể email có tồn tại.
- **FR-013**: Với tài khoản không bị admin khoá, hệ thống MUST gửi link đặt lại dùng một lần, hết hạn sau 30 phút; tối thiểu 60 giây giữa hai lần gửi cho cùng email. Link mới làm link cũ của cùng tài khoản hết hiệu lực.
- **FR-014**: Đặt lại mật khẩu thành công MUST: đổi mật khẩu, vô hiệu link, vô hiệu mọi phiên đăng nhập đã cấp trước đó, gỡ khoá tạm và bộ đếm sai, đánh dấu email đã xác thực.

**Khoá tài khoản bởi admin**
- **FR-015**: Admin MUST xem được danh sách người dùng có phân trang, tìm theo email hoặc họ tên, lọc theo trạng thái.
- **FR-016**: Admin MUST khoá được tài khoản kèm lý do (bắt buộc, tối đa 500 ký tự) và mở khoá được. Không được khoá chính mình hoặc tài khoản admin.
- **FR-017**: Khoá tài khoản MUST vô hiệu mọi phiên đã cấp cho tài khoản đó và có hiệu lực ở mọi service ngay từ request kế tiếp.
- **FR-018**: Các service MUST đọc trạng thái người dùng (vai trò, trạng thái, mốc vô hiệu phiên) qua bộ nhớ đệm dùng chung với thời gian sống ngắn; identity-service MUST xoá mục đệm của người dùng mỗi khi trạng thái, vai trò, họ tên hoặc mốc vô hiệu phiên thay đổi.
- **FR-019**: Chỉ người dùng vai trò ADMIN MUST được dùng các chức năng FR-015, FR-016.

**Chung**
- **FR-020**: Mọi link trong email MUST trỏ tới giao diện web (địa chỉ cấu hình được); token trong link MUST là chuỗi ngẫu nhiên khó đoán và MUST NOT được lưu dạng gốc ở phía máy chủ.
- **FR-021**: Lỗi xác thực MUST trả về mã lỗi máy đọc được (ngoài câu thông báo) để giao diện xử lý: chưa xác thực email, khoá tạm, bị admin khoá, link không hợp lệ.
- **FR-022**: Không ghi token, mật khẩu, link đặt lại vào log.

### Key Entities

- **Người dùng (users)**: bổ sung thời điểm xác thực email, lý do và thời điểm bị khoá, mốc vô hiệu phiên (mọi phiên cấp trước mốc này không còn hợp lệ).
- **Token dùng một lần**: loại (xác thực email / đặt lại mật khẩu), người dùng, hạn dùng. Lưu tạm, tự hết hạn.
- **Bộ đếm đăng nhập sai / khoá tạm**: theo email, tự hết hạn.
- **Bản tóm tắt người dùng trong bộ nhớ đệm**: id, email, họ tên, vai trò, trạng thái, mốc vô hiệu phiên.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng mới hoàn tất đăng ký → xác thực → chọn vai trò trong dưới 3 phút (môi trường dev, hộp thư dev).
- **SC-002**: 100% lần đăng nhập thứ 6 trở đi trong cửa sổ khoá tạm bị từ chối, kể cả khi đúng mật khẩu.
- **SC-003**: Sau khi admin khoá, request kế tiếp của người dùng bị khoá ở cả 3 service đều bị từ chối (0 request lọt).
- **SC-004**: Sau khi đặt lại mật khẩu, 100% token phiên cũ bị từ chối.
- **SC-005**: Phản hồi của đăng nhập sai, quên mật khẩu, gửi lại email xác thực không phân biệt được email tồn tại hay không.
- **SC-006**: Khi bộ nhớ đệm có dữ liệu, recruitment-service và interview-service không gọi identity-service để xác thực request.

## Assumptions

- Môi trường dev dùng hộp thư giả lập chạy kèm hệ thống (không cần SMTP thật); môi trường thật cấu hình SMTP qua biến môi trường.
- Giao diện quản trị danh sách người dùng / khoá tài khoản **ngoài phạm vi** đợt này (khu `/admin` là task FE-01 riêng); admin thao tác qua API. Đợt này chỉ làm giao diện cho đăng ký, xác thực email, đăng nhập, quên và đặt lại mật khẩu.
- Không làm refresh token, đăng xuất phía server, đổi mật khẩu khi đang đăng nhập, đăng nhập mạng xã hội, CAPTCHA, khoá theo IP.
- Ngưỡng 5 lần / 15 phút, hạn link 24 giờ / 30 phút, giãn cách gửi 60 giây là mặc định cấu hình được.
- Tài khoản ADMIN vẫn chỉ tạo bằng seed.
- Mật khẩu tài khoản seed (`demo1234`) đã thoả quy tắc FR-005; quy tắc chỉ áp dụng khi đặt mật khẩu mới.
