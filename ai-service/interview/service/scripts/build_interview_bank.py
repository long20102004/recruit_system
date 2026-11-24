"""Generate a versioned synthetic practice bank, labelled answers and Flyway seed.
No existing questions/answers are replaced. Labels are rubric-derived, NOT human ratings.
"""
from pathlib import Path
import csv, itertools, json
ROOT = Path(__file__).resolve().parents[1]
# skill, level, type, question, three (correct statement, paraphrase, misconception, hints).
BANK = [
('Java','Intern','KNOWLEDGE','Phân biệt == và equals trong Java. Khi so sánh String nên dùng gì?',[
('Với object, == so sánh hai tham chiếu có trỏ cùng đối tượng hay không.','Hai biến object dùng == để kiểm tra cùng địa chỉ tham chiếu.','== luôn so sánh nội dung của mọi object.',['tham chiếu','cùng đối tượng','reference']),
('equals có thể được override để so sánh giá trị logic; String.equals so sánh nội dung chuỗi.','So nội dung hai chuỗi bằng String.equals thay vì so địa chỉ.','String.equals chỉ so sánh địa chỉ bộ nhớ.',['equals','nội dung','override']),
('Dùng Objects.equals(a,b) để so sánh an toàn khi có null.','Objects.equals xử lý được trường hợp một chuỗi là null.','Gọi a.equals(b) luôn an toàn dù a là null.',['Objects.equals','null','an toàn'])]),
('Java','Junior','APPLICATION','Khi dùng HashMap với key là object tự định nghĩa, cần chú ý equals và hashCode thế nào?',[
('Hai object equals nhau phải có cùng hashCode.','Nếu equals trả true thì mã băm của hai key phải giống nhau.','Hai object equals nhau được phép có hashCode khác nhau.',['equals','hashCode','cùng']),
('HashMap dùng hashCode chọn bucket rồi equals để phân biệt key trong bucket.','Mã băm chọn nhóm lưu trữ, còn equals xác định đúng khóa khi va chạm.','Chỉ cần hashCode giống nhau là HashMap coi hai key bằng nhau.',['bucket','va chạm','equals']),
('Tránh thay đổi các trường tham gia equals và hashCode sau khi key đã được đưa vào map.','Nên dùng key bất biến để không làm mất khả năng tìm kiếm sau khi chèn.','Thay đổi key trong map không bao giờ ảnh hưởng việc tra cứu.',['bất biến','thay đổi','tra cứu'])]),
('Java','Middle','SCENARIO','Một bộ đếm dùng chung giữa nhiều thread bị sai số. Bạn phân tích và sửa thế nào?',[
('Phép tăng count++ gồm nhiều thao tác nên có thể xảy ra race condition.','Đọc, cộng rồi ghi không phải một thao tác nguyên tử khi nhiều luồng chạy.','count++ luôn là thao tác nguyên tử trong Java.',['race condition','nguyên tử','nhiều thao tác']),
('Dùng AtomicInteger hoặc synchronized phù hợp để bảo vệ thao tác cập nhật.','Có thể dùng compare-and-set qua AtomicInteger hoặc khóa đồng bộ.','Chỉ thêm volatile là đủ để count++ luôn chính xác.',['AtomicInteger','synchronized','khóa']),
('Đo tải và kiểm thử đồng thời; cân nhắc LongAdder khi tranh chấp cao.','Cần stress test nhiều luồng và đo contention trước khi chọn cách tối ưu.','Không cần kiểm thử đồng thời sau khi thêm khóa.',['kiểm thử','LongAdder','tranh chấp'])]),
('Spring Boot','Intern','KNOWLEDGE','Spring Boot giúp khởi tạo ứng dụng Spring như thế nào?',[
('Spring Boot được xây trên Spring Framework, không thay thế cơ chế IoC của Spring.','Boot bổ sung tiện ích lên nền Spring và vẫn dùng container quản lý bean.','Spring Boot là một ngôn ngữ lập trình độc lập.',['Spring Framework','IoC','bean']),
('Auto-configuration cấu hình theo classpath và điều kiện, có thể bị cấu hình người dùng thay thế.','Boot tự cấu hình có điều kiện dựa vào dependency và cấu hình hiện có.','Auto-configuration luôn ghi đè mọi cấu hình người dùng.',['auto-configuration','điều kiện','classpath']),
('Starter gom dependency; embedded server giúp đóng gói ứng dụng chạy độc lập.','Starter giảm việc khai báo thư viện và Tomcat nhúng giúp chạy bằng java -jar.','Mọi ứng dụng Spring Boot bắt buộc phải triển khai lên Tomcat bên ngoài.',['starter','embedded','Tomcat'])]),
('Spring Boot','Junior','APPLICATION','Vì sao nên dùng constructor injection cho dependency bắt buộc?',[
('Dependency được khai báo rõ trong constructor và có thể giữ trong trường final.','Hàm khởi tạo thể hiện rõ thành phần bắt buộc, hỗ trợ tính bất biến.','Constructor injection bắt buộc dependency phải được tạo bằng new trong service.',['constructor','final','bắt buộc']),
('Có thể truyền mock trực tiếp khi unit test mà không cần dựng Spring context.','Kiểm thử đơn vị chỉ cần khởi tạo service với dependency giả lập.','Constructor injection khiến không thể dùng mock trong unit test.',['mock','unit test','kiểm thử']),
('Vòng phụ thuộc constructor cần được xử lý bằng cách xem lại thiết kế.','Nếu hai service đòi nhau ở hàm tạo thì nên tách trách nhiệm để bỏ vòng phụ thuộc.','Vòng phụ thuộc constructor luôn được Spring tự giải quyết.',['vòng phụ thuộc','thiết kế','tách'])]),
('Spring Boot','Middle','SCENARIO','Một phương thức @Transactional gọi nội bộ phương thức khác nhưng rollback không như mong đợi. Bạn kiểm tra gì?',[
('Proxy-based AOP không chặn self-invocation qua this nên annotation ở lời gọi nội bộ có thể không có hiệu lực.','Gọi trong cùng đối tượng có thể bỏ qua proxy giao dịch của Spring.','Mọi self-invocation đều đi qua proxy @Transactional.',['proxy','self-invocation','cùng đối tượng']),
('Kiểm tra loại exception và rollbackFor vì checked exception mặc định không gây rollback.','Cần xem exception là checked hay runtime và quy tắc rollback đã cấu hình.','Mọi checked exception đều tự động rollback theo mặc định.',['checked','rollbackFor','exception']),
('Kiểm thử tích hợp trạng thái database và cân nhắc tách lời gọi sang bean khác.','Xác minh dữ liệu sau lỗi và đưa ranh giới giao dịch qua một bean phù hợp.','Chỉ xem log là đủ để khẳng định transaction đã rollback.',['kiểm thử','database','bean khác'])]),
('SQL','Intern','KNOWLEDGE','INNER JOIN và LEFT JOIN khác nhau thế nào?',[
('INNER JOIN chỉ giữ các cặp dòng thỏa điều kiện nối ở cả hai bảng.','Nối trong chỉ trả các bản ghi có đối tác khớp.','INNER JOIN luôn giữ toàn bộ dòng bảng trái.',['INNER JOIN','khớp','cả hai']),
('LEFT JOIN giữ mọi dòng bảng trái; cột phía phải là NULL khi không có dòng khớp.','Nối trái vẫn giữ bản ghi không tìm được đối tác và điền NULL ở bên phải.','LEFT JOIN loại bỏ mọi dòng không có bản ghi phía phải.',['LEFT JOIN','NULL','bảng trái']),
('Điều kiện WHERE trên cột bảng phải có thể loại dòng NULL và thay đổi ý nghĩa LEFT JOIN.','Đặt lọc bên phải trong WHERE cần cẩn thận vì có thể làm mất các dòng chưa khớp.','Đặt điều kiện bên phải ở WHERE hay ON luôn cho cùng kết quả.',['WHERE','ON','điều kiện'])]),
('SQL','Junior','APPLICATION','Khi nào nên tạo index và làm sao kiểm tra index có hữu ích?',[
('Xem các cột thường lọc WHERE, nối JOIN hoặc sắp xếp để chọn index phù hợp.','Tạo chỉ mục theo mẫu truy vấn thực tế, nhất là điều kiện tìm kiếm và liên kết.','Nên tạo index cho mọi cột bất kể truy vấn.',['WHERE','JOIN','truy vấn']),
('Index tốn dung lượng và làm tăng chi phí INSERT UPDATE DELETE.','Chỉ mục tăng tốc đọc nhưng phải đánh đổi bộ nhớ và công cập nhật khi ghi.','Index luôn tăng tốc cả đọc và ghi mà không tốn dung lượng.',['dung lượng','ghi','UPDATE']),
('Dùng EXPLAIN và đo thời gian trước sau trên dữ liệu đại diện.','Kiểm tra execution plan và benchmark thay vì đoán index đã được dùng.','Có index thì không cần xem execution plan hay đo lại.',['EXPLAIN','đo','plan'])]),
('SQL','Middle','SCENARIO','Hai yêu cầu đặt hàng đồng thời có thể bán vượt tồn kho. Bạn xử lý ở database thế nào?',[
('Cần giữ thao tác kiểm tra và trừ tồn kho trong cùng ranh giới transaction.','Đọc lượng tồn rồi cập nhật riêng rẽ có thể tạo race condition nên cần giao dịch nhất quán.','Chỉ kiểm tra tồn kho ở giao diện là đủ để tránh bán vượt.',['transaction','đồng thời','kiểm tra']),
('Dùng UPDATE có điều kiện stock >= quantity và kiểm tra số dòng cập nhật hoặc khóa dòng phù hợp.','Có thể cập nhật nguyên tử kèm điều kiện số lượng thay vì đọc rồi ghi không bảo vệ.','Luôn đọc stock bằng SELECT thường rồi UPDATE là an toàn với mọi mức cô lập.',['UPDATE','điều kiện','khóa']),
('Xử lý retry có giới hạn cho deadlock và kiểm tra tính idempotent khi gửi lại yêu cầu.','Khi có bế tắc cần retry có kiểm soát và tránh trừ kho hai lần cho một yêu cầu.','Retry vô hạn không cần idempotency là cách xử lý deadlock tốt nhất.',['deadlock','retry','idempotent'])]),
('REST API','Intern','KNOWLEDGE','Phân biệt GET, POST, PUT và DELETE trong API HTTP.',[
('GET dùng đọc tài nguyên và không nên tạo tác dụng phụ thay đổi dữ liệu nghiệp vụ.','Yêu cầu lấy dữ liệu cần giữ tính an toàn, không dùng GET để xóa bản ghi.','GET nên được dùng để xóa hoặc tạo dữ liệu.',['GET','đọc','an toàn']),
('POST thường tạo hoặc xử lý yêu cầu; PUT thường thay thế trạng thái tại URI xác định.','POST gửi thao tác còn PUT ghi trạng thái của tài nguyên có địa chỉ đã biết.','PUT chỉ được dùng để đọc dữ liệu.',['POST','PUT','tài nguyên']),
('PUT và DELETE có ngữ nghĩa idempotent; phản hồi HTTP có thể khác giữa các lần gọi.','Gọi lặp PUT hoặc DELETE phải giữ cùng tác động cuối, không bắt buộc mã trả về giống nhau.','Idempotent có nghĩa mọi lần gọi phải trả cùng mã HTTP.',['idempotent','DELETE','tác động'])]),
('REST API','Junior','APPLICATION','Bạn thiết kế API tạo đơn hàng với validation và phản hồi lỗi thế nào?',[
('Kiểm tra kiểu dữ liệu, số lượng và ràng buộc nghiệp vụ phía server.','Không tin validation frontend; server cần xác minh đầu vào và điều kiện nghiệp vụ.','Chỉ cần validation phía frontend vì người dùng không thể bỏ qua.',['server','validation','nghiệp vụ']),
('Dùng mã HTTP phù hợp và cấu trúc lỗi nhất quán có thông tin trường sai.','Phân biệt lỗi đầu vào với lỗi hệ thống, trả lỗi có cấu trúc để client xử lý.','Mọi lỗi nghiệp vụ nên trả HTTP 200 mà không có thông tin lỗi.',['HTTP','cấu trúc','lỗi']),
('Bảo vệ retry tạo đơn bằng idempotency key hoặc khóa nghiệp vụ duy nhất.','Một yêu cầu gửi lại không nên tạo hai đơn; có thể dùng mã chống trùng.','Mỗi retry luôn phải tạo thêm một đơn hàng mới.',['idempotency','retry','duy nhất'])]),
('REST API','Middle','SCENARIO','Một API phụ thuộc dịch vụ ngoài thường timeout. Bạn làm gì để tránh lỗi dây chuyền?',[
('Đặt timeout kết nối và đọc hữu hạn cho lời gọi ra ngoài.','Cần giới hạn thời gian chờ để luồng xử lý không bị giữ vô hạn.','Không đặt timeout giúp hệ thống ổn định hơn.',['timeout','giới hạn','kết nối']),
('Chỉ retry lỗi tạm thời có backoff và giới hạn; cân nhắc idempotency.','Thử lại có khoảng nghỉ tăng dần, tránh retry thao tác không an toàn.','Retry mọi lỗi liên tục không giới hạn là cách tránh quá tải.',['retry','backoff','idempotency']),
('Dùng circuit breaker hoặc bulkhead, theo dõi metric và báo lỗi phụ thuộc rõ ràng.','Cô lập tài nguyên và ngắt tạm dịch vụ lỗi để bảo vệ phần còn lại.','Một dịch vụ lỗi nên chiếm toàn bộ thread pool của hệ thống.',['circuit breaker','bulkhead','metric'])]),
('Python','Intern','KNOWLEDGE','List và tuple trong Python khác nhau thế nào?',[
('List có thể thay đổi phần tử và kích thước sau khi tạo.','Danh sách là cấu trúc mutable cho phép thêm và sửa dữ liệu.','List là immutable và không thể thêm phần tử.',['list','mutable','thay đổi']),
('Tuple không cho gán lại các phần tử của nó sau khi tạo.','Bộ tuple giữ cấu trúc phần tử bất biến ở cấp container.','Tuple cho phép gán lại từng phần tử bằng chỉ số.',['tuple','bất biến','gán lại']),
('Tuple chỉ hashable nếu tất cả phần tử bên trong cũng hashable.','Không phải tuple nào cũng làm key dictionary được; tuple chứa list không hash được.','Mọi tuple đều hashable kể cả tuple chứa list.',['hashable','key','phần tử'])]),
('Python','Junior','APPLICATION','Vì sao đối số mặc định là list có thể gây lỗi? Bạn sửa thế nào?',[
('Giá trị mặc định được tạo khi định nghĩa hàm và có thể được dùng lại giữa các lời gọi.','List mặc định là một đối tượng dùng chung, không tự tạo mới mỗi lần gọi.','Python luôn tạo list mặc định mới cho từng lời gọi.',['mặc định','dùng chung','định nghĩa']),
('Sửa bằng mặc định None rồi tạo list mới bên trong khi chưa có giá trị.','Dùng sentinel như None và khởi tạo danh sách trong thân hàm.','Thay list mặc định bằng một list rỗng khác trong chữ ký luôn giải quyết được lỗi.',['None','list mới','bên trong']),
('Viết test nhiều lần gọi để kiểm tra dữ liệu không rò từ lần trước.','Kiểm thử hai lần gọi độc lập giúp phát hiện trạng thái bị chia sẻ ngoài ý muốn.','Chỉ test một lần gọi là đủ để phát hiện mọi lỗi mặc định mutable.',['test','nhiều lần','độc lập'])]),
('Python','Middle','SCENARIO','Một tác vụ Python xử lý CPU chậm: nên dùng thread hay process?',[
('Trong CPython có GIL truyền thống, thread Python không tự tăng tốc mã Python CPU-bound.','Nhiều luồng không bảo đảm song song CPU cho bytecode khi GIL còn bật.','GIL giúp mọi thread Python luôn chạy CPU song song hoàn toàn.',['GIL','CPU-bound','thread']),
('Cân nhắc multiprocessing hoặc thư viện native giải phóng GIL cho phần CPU nặng.','Có thể chia việc sang nhiều tiến trình hoặc dùng phép toán native phù hợp.','Multiprocessing luôn dùng chung mọi object mà không có chi phí trao đổi.',['multiprocessing','native','tiến trình']),
('Profile trước và đo chi phí truyền dữ liệu, bộ nhớ để chọn phương án.','Đo điểm nghẽn và overhead liên tiến trình thay vì chỉ tăng số worker.','Tăng worker vô hạn luôn tăng hiệu năng tuyến tính.',['profile','bộ nhớ','chi phí'])]),
('React','Intern','KNOWLEDGE','Props và state khác nhau thế nào trong React?',[
('Props là dữ liệu truyền từ component cha và được xem là chỉ đọc trong component nhận.','Component con nhận đầu vào từ cha và không tự sửa trực tiếp props.','Component con nên sửa trực tiếp props để cập nhật cha.',['props','cha','chỉ đọc']),
('State là dữ liệu component quản lý và cập nhật qua setter hoặc reducer.','Trạng thái nội bộ cần thay đổi bằng API cập nhật state của React.','Nên sửa trực tiếp object state mà không gọi setter.',['state','setter','reducer']),
('Thay đổi props hoặc state có thể khiến React render lại giao diện.','React dựng lại UI theo dữ liệu mới khi trạng thái hoặc đầu vào đổi.','Thay đổi state không bao giờ làm component render lại.',['render','giao diện','thay đổi'])]),
('React','Junior','APPLICATION','Khi fetch dữ liệu trong useEffect, bạn tránh race condition thế nào?',[
('Khai báo dependency đúng để effect phản ánh giá trị dùng trong lời gọi.','Danh sách phụ thuộc phải khớp dữ liệu mà effect sử dụng.','Luôn để dependency rỗng dù effect dùng biến thay đổi.',['dependency','effect','phụ thuộc']),
('Hủy request bằng AbortController hoặc bỏ qua response cũ sau cleanup.','Cần ngăn kết quả của yêu cầu cũ ghi đè kết quả mới khi component đổi.','Response đến sau luôn phải ghi đè dữ liệu bất kể request nào mới.',['AbortController','cleanup','response cũ']),
('Hiển thị trạng thái loading và xử lý lỗi để UI không treo hoặc báo thành công giả.','UI cần phản ánh đang tải, thất bại và cho phép thử lại hợp lý.','Có thể bỏ qua mọi lỗi fetch mà vẫn báo thành công.',['loading','lỗi','UI'])]),
('React','Middle','SCENARIO','Danh sách lớn render chậm. Bạn phân tích và tối ưu React thế nào?',[
('Dùng React Profiler để xác định component render tốn thời gian.','Cần đo lại số lần render và phần chậm trước khi thêm tối ưu.','Luôn thêm useMemo cho mọi biểu thức mà không cần đo.',['Profiler','đo','render']),
('Dùng key ổn định và cân nhắc virtualization cho danh sách dài.','Chỉ render phần danh sách nhìn thấy và giữ định danh item ổn định.','Dùng index làm key luôn đúng cả khi danh sách sắp xếp lại.',['key','virtualization','danh sách']),
('Chỉ dùng memoization khi có lợi và kiểm tra dependency cùng tính đúng đắn.','Memo cần giữ kết quả đúng và phải được chứng minh giảm chi phí thực tế.','Memoization không có chi phí và không thể gây dữ liệu cũ.',['memo','dependency','đúng'])]),
('Docker','Intern','KNOWLEDGE','Image, container và volume trong Docker khác nhau thế nào?',[
('Image là mẫu filesystem và cấu hình dùng tạo container.','Ảnh container là bản mẫu để khởi tạo tiến trình có môi trường xác định.','Image là một tiến trình đang chạy trên máy.',['image','mẫu','container']),
('Container là instance chạy từ image và có lớp ghi riêng.','Container là thực thể được tạo từ image với vòng đời riêng.','Xóa container luôn xóa toàn bộ dữ liệu của mọi volume.',['container','instance','lớp ghi']),
('Volume lưu dữ liệu cần tồn tại ngoài vòng đời container.','Database nên có vùng lưu bền vững độc lập với việc tạo lại container.','Dữ liệu database chỉ nên lưu ở lớp ghi tạm của container.',['volume','dữ liệu','vòng đời'])]),
('Docker','Junior','APPLICATION','Ứng dụng trong container kết nối database khác container như thế nào?',[
('Dùng tên service và cổng bên trong trên cùng mạng Compose.','Các container cùng network tìm nhau bằng DNS service thay vì IP cố định.','Container luôn dùng localhost để gọi database ở container khác.',['service','network','DNS']),
('Phân biệt published port của host với port mà container lắng nghe.','Cổng host phục vụ truy cập bên ngoài, còn nội bộ dùng cổng dịch vụ.','Cổng host và cổng container bắt buộc luôn giống nhau.',['host','port','nội bộ']),
('Chờ readiness và xử lý kết nối lỗi vì thứ tự tạo container không bảo đảm dịch vụ đã sẵn sàng.','Cần healthcheck và retry hữu hạn thay vì chỉ dựa vào depends_on dạng đơn giản.','Container đã được tạo nghĩa là database đã sẵn sàng nhận truy vấn.',['healthcheck','readiness','retry'])]),
('Docker','Middle','SCENARIO','Máy bị lag khi build và chạy nhiều model trong Docker. Bạn xử lý thế nào?',[
('Đo CPU RAM swap và I/O bằng công cụ hệ thống hoặc docker stats trước.','Xác định nghẽn bộ nhớ hay tính toán bằng số đo thay vì quy hết cho Docker.','Di chuyển sang ổ lớn hơn luôn làm giảm mức dùng RAM của model.',['CPU','RAM','swap']),
('Giới hạn song song lúc build, worker và thread suy luận để tránh chiếm hết tài nguyên.','Giảm số tác vụ đồng thời và đặt ngân sách tài nguyên cho dịch vụ nặng.','Càng nhiều worker và thread luôn càng ít lag.',['song song','thread','giới hạn']),
('Tái sử dụng image và cache model, không build lại khi chỉ cần start container.','Tách bước build khỏi khởi động và lưu cache để tránh tải hoặc biên dịch lặp lại.','Mỗi lần khởi động đều bắt buộc rebuild toàn bộ image.',['cache','build','start'])]),
('Git','Intern','KNOWLEDGE','Working tree, staging area và commit khác nhau thế nào?',[
('Working tree chứa các file đang được chỉnh sửa.','Cây làm việc là nội dung file hiện tại trên máy.','Sửa file tự động tạo một commit mới.',['working tree','file','chỉnh sửa']),
('Staging area chọn phiên bản thay đổi sẽ đưa vào commit tiếp theo.','git add chuẩn bị đúng phần thay đổi muốn ghi nhận.','git add tự động đẩy code lên remote.',['staging','git add','commit']),
('Commit lưu snapshot có lịch sử để có thể so sánh và truy vết.','Mỗi commit ghi trạng thái được chọn kèm thông tin lịch sử.','Commit chỉ lưu trên RAM và mất khi tắt máy.',['snapshot','lịch sử','commit'])]),
('Git','Junior','APPLICATION','Bạn xử lý merge conflict mà vẫn giữ thay đổi đúng của cả hai phía như thế nào?',[
('Đọc các phần xung đột và hiểu ý nghĩa thay đổi thay vì chọn một phía máy móc.','Cần so sánh ngữ cảnh và mục tiêu của hai phiên bản.','Luôn chọn ours cho mọi conflict là cách đúng.',['xung đột','hai','ngữ cảnh']),
('Sửa nội dung, bỏ conflict markers rồi stage và hoàn thành merge.','Sau khi hòa giải cần git add và kết thúc thao tác merge đúng trạng thái.','Để nguyên conflict markers rồi commit vẫn là kết quả hợp lệ.',['markers','stage','merge']),
('Chạy kiểm thử phần bị ảnh hưởng và kiểm tra diff trước khi chia sẻ.','Xác minh code sau gộp vẫn đúng bằng test và review thay đổi.','Merge thành công nghĩa là không cần chạy test.',['test','diff','kiểm tra'])]),
('Git','Middle','SCENARIO','Một commit lỗi đã được nhiều người pull. Bạn rollback thế nào?',[
('Ưu tiên git revert để tạo commit đảo thay đổi mà không viết lại lịch sử chung.','Nhánh đã chia sẻ thường nên hoàn tác bằng một commit mới.','Luôn reset hard và force push nhánh chung mà không trao đổi.',['revert','lịch sử','commit mới']),
('Xác định phạm vi lỗi, dependency và kiểm thử bản hoàn tác.','Cần kiểm tra các commit liên quan và tác động khi đảo thay đổi.','Revert không thể gây conflict hoặc ảnh hưởng commit khác.',['phạm vi','kiểm thử','liên quan']),
('Trao đổi với nhóm và theo dõi triển khai sau khi hoàn tác.','Cần thông báo thay đổi và xác minh hệ thống hoạt động sau rollback.','Hoàn tác trên Git tự động bảo đảm mọi môi trường đã phục hồi.',['nhóm','triển khai','theo dõi'])]),
('Security','Intern','KNOWLEDGE','Authentication và authorization khác nhau thế nào?',[
('Authentication xác minh danh tính người dùng hoặc dịch vụ.','Xác thực trả lời người gọi là ai.','Authentication quyết định mọi quyền truy cập tài nguyên.',['authentication','danh tính','xác thực']),
('Authorization kiểm tra quyền thực hiện thao tác lên tài nguyên.','Phân quyền xác định người đã xác thực có được làm hành động đó không.','Đăng nhập thành công đồng nghĩa được truy cập mọi tài nguyên.',['authorization','quyền','tài nguyên']),
('Cần kiểm tra quyền phía server cho từng thao tác và phạm vi sở hữu.','Ẩn nút ở frontend không thay thế kiểm tra quyền trên API.','Chỉ ẩn nút frontend là đủ để bảo vệ dữ liệu.',['server','sở hữu','API'])]),
('Security','Junior','APPLICATION','Bạn bảo vệ API xem hồ sơ ứng viên khỏi truy cập trái phép thế nào?',[
('Xác minh token hợp lệ và trạng thái tài khoản trước khi xử lý.','API cần kiểm chữ ký, hạn token và tài khoản còn được phép dùng.','Chỉ cần giải mã payload JWT mà không xác minh chữ ký.',['token','chữ ký','hạn']),
('Kiểm tra quyền sở hữu hoặc quan hệ tuyển dụng trên từng ID hồ sơ.','Không tin candidateId do client gửi; cần đối chiếu phạm vi người gọi.','Biết ID hồ sơ là đủ để được quyền đọc hồ sơ đó.',['sở hữu','candidateId','quyền']),
('Chỉ trả dữ liệu cần thiết và tránh ghi nội dung CV nhạy cảm vào log.','Giảm dữ liệu cá nhân trong response và log giúp hạn chế lộ thông tin.','Nên log toàn bộ CV và token để dễ debug.',['dữ liệu','log','nhạy cảm'])]),
('Security','Middle','SCENARIO','Một access token bị lộ. Bạn giảm thiệt hại và phòng ngừa thế nào?',[
('Thu hồi phiên hoặc token liên quan và kiểm tra dấu hiệu lạm dụng.','Cần chặn credential bị lộ và xác định phạm vi truy cập bất thường.','Đổi mật khẩu luôn tự làm mọi JWT đang phát hành hết hiệu lực.',['thu hồi','token','lạm dụng']),
('Dùng thời hạn access token ngắn và cơ chế refresh có kiểm soát.','Giới hạn cửa sổ rủi ro bằng TTL ngắn và quản lý vòng đời refresh token.','Access token không hết hạn là cách an toàn nhất.',['thời hạn','refresh','ngắn']),
('Rà soát nơi lưu token, HTTPS, log và quy trình xử lý sự cố.','Cần tìm nguồn lộ ở client, truyền tải hoặc logging rồi khắc phục.','HTTPS làm việc lưu token công khai trong log trở nên an toàn.',['HTTPS','log','sự cố'])]),
('Machine Learning','Intern','KNOWLEDGE','Train, validation và test có vai trò gì khi đánh giá mô hình?',[
('Train dùng học tham số mô hình.','Tập huấn luyện cung cấp ví dụ để tối ưu trọng số.','Tập test nên được dùng để học trọng số trong mỗi epoch.',['train','tham số','huấn luyện']),
('Validation dùng chọn cấu hình và checkpoint, không thay thế test độc lập.','Tập phát triển phục vụ chọn siêu tham số mà chưa mở tập đánh giá cuối.','Chọn siêu tham số trực tiếp theo test không tạo ra thiên lệch.',['validation','checkpoint','siêu tham số']),
('Test được giữ độc lập và tránh để các biến thể cùng nguồn rò giữa các tập.','Đánh giá cuối cần dữ liệu chưa dùng lựa chọn mô hình và tách theo thực thể nguồn.','Chia ngẫu nhiên các bản sao gần giống sang train và test luôn là đánh giá độc lập.',['test','độc lập','rò'])]),
('Machine Learning','Junior','APPLICATION','Bạn đánh giá một bộ chấm câu trả lời phỏng vấn tự động như thế nào?',[
('So sánh điểm mô hình với điểm người chấm độc lập bằng MAE và phân tích sai số.','Cần nhãn chuyên gia và xem độ lệch điểm chứ không chỉ xem vài ví dụ đẹp.','Nhãn tự sinh luôn tương đương đánh giá của chuyên gia.',['MAE','người chấm','sai số']),
('Tách test theo câu hỏi để tránh câu trả lời biến thể làm rò dữ liệu.','Các phiên bản đáp án cho một câu cần nằm cùng nhóm khi chia tập.','Chia từng dòng ngẫu nhiên luôn ngăn mọi dạng rò dữ liệu.',['câu hỏi','nhóm','rò']),
('Kiểm tra câu diễn đạt lại, phủ định, sai kiến thức và trường hợp ngoài miền.','Bộ thử cần có paraphrase, câu sai nhưng giống từ và chủ đề lạ.','Tương đồng ngữ nghĩa cao luôn chứng minh câu trả lời đúng chuyên môn.',['phủ định','diễn đạt','ngoài miền'])]),
('Machine Learning','Middle','SCENARIO','Model có điểm test tổng hợp cao nhưng chấm CV hoặc phỏng vấn thật kém. Bạn làm gì?',[
('Kiểm tra domain shift và dữ liệu rò giữa train với test.','Cần xem dữ liệu thật khác mẫu tổng hợp ở ngôn ngữ, bố cục hay phân phối ra sao.','Điểm cao trên dữ liệu tổng hợp bảo đảm chất lượng trên người dùng thật.',['domain shift','dữ liệu','rò']),
('Thu thập mẫu thật có nhãn độc lập và đánh giá theo từng nhóm lỗi.','Cần bộ đánh giá đại diện cùng phân tích theo trường, chủ đề hoặc cấp độ.','Chỉ tăng số mẫu tổng hợp giống nhau sẽ sửa mọi lỗi thực tế.',['nhãn','thật','lỗi']),
('So sánh baseline, hiệu chỉnh ngưỡng trên validation và giữ test cuối độc lập.','Đo cải thiện với phương án đơn giản, chọn ngưỡng ở dev rồi đánh giá lại trên test chưa dùng.','Có thể điều chỉnh ngưỡng theo test nhiều lần rồi coi test vẫn độc lập.',['baseline','ngưỡng','validation'])]),
]

def main():
    questions=[]; answers=[]
    for index,(skill,level,kind,text,criteria) in enumerate(BANK,1):
        key=f'm3-v2-{index:03d}'
        rubric=[{'key':f'c{j+1}','label':statement,'weight':w,'hints':hints,
                 'reference_answers':[statement,paraphrase],'misconceptions':[wrong]}
                for j,((statement,paraphrase,wrong,hints),w) in enumerate(zip(criteria,[.4,.35,.25]))]
        reference=' '.join(c[0] for c in criteria)
        questions.append({'id':key,'skill':skill,'topic':skill,'seniority':level,'difficulty':{'Intern':'Easy','Junior':'Medium','Middle':'Hard'}[level],
            'question_type':kind,'question':text,'reference_answer':reference,'criteria':rubric,'source':'synthetic-ai-v2','review_status':'needs_expert_review'})
        def add(answer,score,variant,covered):
            answers.append({'id':f'{key}-{variant}','question_id':key,'rank_target':level,'answer':answer,'target_score':round(score,2),
                'target_covered_keys':';'.join(f'c{i+1}' for i in covered),'label_source':'synthetic_rubric','variant':variant})
        for n in [1,2,3]:
            for subset in itertools.combinations(range(3),n):
                add(' '.join(criteria[i][0] for i in subset),10*sum(rubric[i]['weight'] for i in subset),'correct-'+''.join(map(str,subset)),subset)
        add(' '.join(c[1] for c in criteria),10,'paraphrase',range(3))
        add(' '.join(c[2] for c in criteria),0,'misconceptions',[])
        add('Tôi chưa biết cách giải thích vấn đề này.',0,'unknown',[])
        add('Tôi thích thể thao và nghe nhạc vào cuối tuần.',0,'offtopic',[])
        add(', '.join(h for c in criteria for h in c[3]),1,'keyword-stuffing',[])
        add(criteria[0][0]+' '+criteria[1][2],4,'mixed',[0])
    bundle={'meta':{'version':'module3-bank-v2','role':'IT practice','provenance':'AI-generated synthetic questions and rubric-derived labels; not expert-validated',
        'n_questions':len(questions),'label_field':'target_score','review_required':True},'questions':questions}
    data=ROOT/'data';(data/'interview_bank_v2.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
    with (data/'interview_answers_v2.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(answers[0]));writer.writeheader();writer.writerows(answers)
    def sql(value):return "'"+str(value).replace('\\','\\\\').replace("'","''")+"'"
    migration=ROOT.parent/'backend/interview-service/src/main/resources/db/migration/V4__interview_bank_and_assessment.sql'
    ddl='''-- AI-generated practice bank. Targets are synthetic, not human grades.
ALTER TABLE interview_questions ADD COLUMN external_key VARCHAR(80) NULL UNIQUE,
 ADD COLUMN skill VARCHAR(120) NULL, ADD COLUMN seniority VARCHAR(32) NOT NULL DEFAULT 'Junior',
 ADD COLUMN source VARCHAR(80) NOT NULL DEFAULT 'legacy';
ALTER TABLE evaluation_rubrics ADD COLUMN reference_answers JSON NULL, ADD COLUMN misconceptions JSON NULL;
ALTER TABLE evaluation_results ADD COLUMN scoring_mode VARCHAR(32) NULL,
 ADD COLUMN scoring_model_version VARCHAR(255) NULL, ADD COLUMN criterion_results JSON NULL,
 ADD COLUMN coverage_score DECIMAL(6,4) NULL;
ALTER TABLE interview_sessions ADD COLUMN recruiter_user_id INT NULL;
'''
    lines=[ddl]
    for q in questions:
        vals=[q['id'],q['question'],q['question'],q['topic'],q['difficulty'],q['question_type'],q['reference_answer'],q['skill'],q['seniority'],q['source']]
        lines.append('INSERT INTO interview_questions (external_key,title,question_text,topic,difficulty,question_type,reference_answer,skill,seniority,source,max_score,is_active) VALUES ('+','.join(map(sql,vals))+',10,1);')
        lines.append('SET @question_id = LAST_INSERT_ID();')
        for c in q['criteria']:
            vals=[c['label'],c['reference_answers'][0],10*c['weight'],c['weight'],json.dumps(c['hints'],ensure_ascii=False),json.dumps(c['reference_answers'],ensure_ascii=False),json.dumps(c['misconceptions'],ensure_ascii=False)]
            lines.append('INSERT INTO evaluation_rubrics (question_id,criterion_name,criterion_description,max_score,weight,expected_keywords,reference_answers,misconceptions) VALUES (@question_id,'+','.join(map(sql,vals))+');')
    migration.write_text('\n'.join(lines)+'\n')
    (data/'interview_bank_v2_seed.sql').write_text('\n'.join(lines[1:])+'\n')
    print(f'{len(questions)} questions, {len(questions)*3} criteria, {len(answers)} synthetic answers; generated JSON/CSV/Flyway V4')
if __name__=='__main__': main()
