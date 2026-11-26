import { mockReject, mockResolve } from "./core";

export type CompanyStatus = "ACTIVE" | "PENDING" | "REJECTED" | "LOCKED";

export interface CompanyLicenseFile {
  name: string;
  meta: string;
}

export interface CompanyDto {
  id: number;
  name: string;
  legalName: string;
  logo: string;
  industry: string;
  size: string;
  city: string;
  tagline: string;
  about: string;
  perks: string[];
  skills: string[];
  founded: number;
  website: string;
  workingDays: string;
  overtime: string;
  address: string;
  workMode: string;
  openJobsCount: number;
  status: CompanyStatus;
  submittedAt: string;
  submittedBy: string;
  taxCode: string;
  email: string;
  phone: string;
  rejectReason: string | null;
  licenseFile: CompanyLicenseFile;
}

export interface CompanyListFilter {
  status?: CompanyStatus | "ALL";
  q?: string;
  city?: string;
  industry?: string;
}

const COMPANIES: CompanyDto[] = [
  {
    id: 1,
    name: "Lumen Fintech",
    legalName: "Công ty Cổ phần Công nghệ Tài chính Lumen",
    logo: "LF",
    industry: "Fintech",
    size: "300–500 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Nền tảng thanh toán cho doanh nghiệp vừa và nhỏ.",
    about:
      "Lumen Fintech xây dựng hạ tầng thanh toán, đối soát và quản lý dòng tiền cho hơn 20.000 doanh nghiệp. Đội ngũ kỹ thuật gồm 180 kỹ sư, làm việc theo mô hình squad với quyền sở hữu sản phẩm rõ ràng.",
    perks: [
      "Hybrid 3/2, laptop và màn hình theo lựa chọn.",
      "Bảo hiểm sức khỏe cho cả gia đình.",
      "Ngân sách học tập 15 triệu/năm.",
    ],
    skills: ["Java", "Spring Boot", "Kafka", "AWS", "ReactJS", "PostgreSQL"],
    founded: 2016,
    website: "lumenfintech.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 12, toà Riverside, 2A Nguyễn Lương Bằng, Quận 7, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 12,
    status: "ACTIVE",
    submittedAt: "2026-10-12T08:30:00",
    submittedBy: "Nguyễn Minh Tuấn (tuan.nguyen@lumenfintech.vn)",
    taxCode: "0314029182",
    email: "hr@lumenfintech.vn",
    phone: "028 5412 8899",
    rejectReason: null,
    licenseFile: { name: "GPKD_LumenFintech.pdf", meta: "2 trang · 1,6 MB" },
  },
  {
    id: 2,
    name: "Nami Commerce",
    legalName: "Công ty TNHH Thương mại Điện tử Nami",
    logo: "NC",
    industry: "Thương mại điện tử",
    size: "500–1000 NV",
    city: "Hà Nội",
    tagline: "Sàn bán lẻ trực tuyến cho hàng tiêu dùng.",
    about:
      "Nami Commerce vận hành hệ sinh thái bán lẻ đa kênh phục vụ hàng triệu đơn hàng mỗi tháng tại Việt Nam. Đội ngũ công nghệ tập trung vào kiến trúc microservices chịu tải cao và tìm kiếm sản phẩm thông minh.",
    perks: [
      "Thưởng hiệu suất 2 lần/năm theo OKR.",
      "Phụ cấp ăn trưa, gửi xe và gói khám sức khoẻ định kỳ.",
      "Câu lạc bộ chạy bộ, cầu lông và tech-talk hàng tuần.",
    ],
    skills: ["ReactJS", "TypeScript", "Go", "MySQL", "Redis"],
    founded: 2018,
    website: "namicommerce.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Hiếm khi, có lương OT",
    address: "Tầng 9, toà Handico, Phạm Hùng, Nam Từ Liêm, Hà Nội",
    workMode: "Product",
    openJobsCount: 9,
    status: "ACTIVE",
    submittedAt: "2026-10-18T14:15:00",
    submittedBy: "Trần Thu Hà (ha.tran@namicommerce.vn)",
    taxCode: "0108349201",
    email: "talent@namicommerce.vn",
    phone: "024 3789 2211",
    rejectReason: null,
    licenseFile: { name: "GPKD_NamiCommerce.pdf", meta: "3 trang · 2,1 MB" },
  },
  {
    id: 3,
    name: "Orbit Analytics",
    legalName: "Công ty Cổ phần Phân tích Dữ liệu Orbit",
    logo: "OA",
    industry: "Dữ liệu & AI",
    size: "50–100 NV",
    city: "Remote",
    tagline: "Phân tích dữ liệu bán lẻ theo thời gian thực.",
    about:
      "Orbit Analytics phát triển nền tảng dữ liệu streaming giúp chuỗi bán lẻ dự báo tồn kho và hành vi khách hàng theo thời gian thực. 100% đội ngũ kỹ sư làm việc linh hoạt theo giờ kết quả.",
    perks: [
      "Làm việc từ xa hoàn toàn, trợ cấp thiết bị tại nhà 10 triệu.",
      "16 ngày phép năm và nghỉ sinh nhật hưởng lương.",
      "Tài trợ chi phí chứng chỉ AWS, GCP và hội thảo AI.",
    ],
    skills: ["Python", "Spark", "ML", "Airflow", "BigQuery"],
    founded: 2021,
    website: "orbitanalytics.io",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "184 Lê Đại Hành, Quận 11, TP. Hồ Chí Minh (Văn phòng đại diện)",
    workMode: "Product",
    openJobsCount: 6,
    status: "ACTIVE",
    submittedAt: "2026-11-02T10:00:00",
    submittedBy: "Lê Hoàng Nam (nam.le@orbitanalytics.io)",
    taxCode: "0316889123",
    email: "jobs@orbitanalytics.io",
    phone: "028 3866 9012",
    rejectReason: null,
    licenseFile: { name: "GPKD_OrbitAnalytics.pdf", meta: "2 trang · 1,2 MB" },
  },
  {
    id: 4,
    name: "Cobalt Cloud",
    legalName: "Công ty TNHH Hạ tầng Đám mây Cobalt",
    logo: "CC",
    industry: "Hạ tầng đám mây",
    size: "100–300 NV",
    city: "Đà Nẵng",
    tagline: "Dịch vụ cloud được quản lý cho startup.",
    about:
      "Cobalt Cloud cung cấp dịch vụ Kubernetes quản lý, quan sát hệ thống và tự động hoá hạ tầng cho hơn 120 startup công nghệ tại Đông Nam Á.",
    perks: [
      "Môi trường kỹ thuật thuần, tự chủ cao và ít họp.",
      "Hỗ trợ chuyển chỗ ở cho kỹ sư đến Đà Nẵng làm việc.",
      "Bảo hiểm tai nạn và sức khoẻ nâng cao.",
    ],
    skills: ["Kubernetes", "Go", "Linux", "Terraform", "Prometheus"],
    founded: 2019,
    website: "cobaltcloud.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Phụ cấp trực on-call rõ ràng",
    address: "Tầng 6, toà Software Park, 02 Quang Trung, Hải Châu, Đà Nẵng",
    workMode: "Product",
    openJobsCount: 5,
    status: "ACTIVE",
    submittedAt: "2026-11-05T11:20:00",
    submittedBy: "Phạm Anh Dũng (dung.pham@cobaltcloud.vn)",
    taxCode: "0401982345",
    email: "careers@cobaltcloud.vn",
    phone: "0236 388 7766",
    rejectReason: null,
    licenseFile: { name: "GPKD_CobaltCloud.pdf", meta: "2 trang · 1,4 MB" },
  },
  {
    id: 5,
    name: "Sao Mai Software",
    legalName: "Công ty Cổ phần Phần mềm Sao Mai",
    logo: "SM",
    industry: "Outsourcing",
    size: "1000+ NV",
    city: "Hà Nội",
    tagline: "Phát triển phần mềm cho khách hàng Nhật Bản.",
    about:
      "Sao Mai Software có hơn 12 năm kinh nghiệm triển khai hệ thống doanh nghiệp, tài chính và sản xuất cho các tập đoàn lớn tại Tokyo và Osaka, với lộ trình thăng tiến BrSE và Tech Lead rõ ràng.",
    perks: [
      "Phụ cấp tiếng Nhật JLPT lên tới 5 triệu/tháng.",
      "Cơ hội onsite ngắn hạn và dài hạn tại Nhật Bản.",
      "Tháng lương 13, thưởng dự án và du lịch công ty.",
    ],
    skills: ["Java", ".NET", "Angular", "Spring Boot", "Oracle"],
    founded: 2014,
    website: "saomaisoft.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Thanh toán 150% – 200% nếu có OT",
    address: "Tầng 15, toà Detech II, 107 Nguyễn Phong Sắc, Cầu Giấy, Hà Nội",
    workMode: "Outsourcing",
    openJobsCount: 15,
    status: "ACTIVE",
    submittedAt: "2026-09-20T09:00:00",
    submittedBy: "Vũ Thị Lan (lan.vu@saomaisoft.vn)",
    taxCode: "0106423118",
    email: "tuyendung@saomaisoft.vn",
    phone: "024 3795 4455",
    rejectReason: null,
    licenseFile: { name: "GPKD_SaoMaiSoftware.pdf", meta: "4 trang · 2,9 MB" },
  },
  {
    id: 6,
    name: "Tidewave Games",
    legalName: "Công ty TNHH Giải trí Số Tidewave",
    logo: "TG",
    industry: "Game",
    size: "100–300 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Studio game mobile thể loại casual.",
    about:
      "Tidewave Games phát triển các tựa game giải đố và mô phỏng đạt hơn 40 triệu lượt tải toàn cầu. Chúng tôi đề cao tinh thần thử nghiệm nhanh và chia sẻ doanh thu dự án.",
    perks: [
      "Thưởng chia sẻ lợi nhuận theo doanh thu game phát hành.",
      "Phòng thư giãn, snack miễn phí và máy chơi game tại văn phòng.",
      "Giờ làm việc linh hoạt 9:30 – 18:30.",
    ],
    skills: ["Unity", "C#", "C++", "Shader", "Firebase"],
    founded: 2020,
    website: "tidewavegames.com",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "72 Nguyễn Thị Minh Khai, Quận 3, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 4,
    status: "ACTIVE",
    submittedAt: "2026-10-28T16:40:00",
    submittedBy: "Đặng Quốc Huy (huy.dang@tidewavegames.com)",
    taxCode: "0316123987",
    email: "hr@tidewavegames.com",
    phone: "028 3930 5544",
    rejectReason: null,
    licenseFile: { name: "GPKD_TidewaveGames.pdf", meta: "2 trang · 1,5 MB" },
  },
  {
    id: 7,
    name: "VeloPay Tech",
    legalName: "Công ty Cổ phần Ví điện tử VeloPay",
    logo: "VP",
    industry: "Fintech",
    size: "100–300 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Giải pháp cổng thanh toán QR và thu hộ tự động.",
    about:
      "VeloPay giúp các chuỗi F&B và bán lẻ kết nối thanh toán tức thời với hơn 35 ngân hàng nội địa, xử lý hàng triệu giao dịch mỗi ngày với độ sẵn sàng 99,99%.",
    perks: [
      "Review lương 2 lần/năm theo năng lực thực tế.",
      "Gói bảo hiểm sức khoẻ Bảo Việt cao cấp.",
      "Làm việc hybrid 2 ngày tại nhà mỗi tuần.",
    ],
    skills: ["Java", "Kotlin", "Kafka", "PostgreSQL", "Docker"],
    founded: 2019,
    website: "velopay.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 8, toà Lim Tower 3, 29A Nguyễn Đình Chiểu, Quận 1, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 8,
    status: "ACTIVE",
    submittedAt: "2026-11-08T09:10:00",
    submittedBy: "Hoàng Gia Bảo (bao.hoang@velopay.vn)",
    taxCode: "0315678123",
    email: "recruit@velopay.vn",
    phone: "028 3822 3344",
    rejectReason: null,
    licenseFile: { name: "GPKD_VeloPay.pdf", meta: "2 trang · 1,7 MB" },
  },
  {
    id: 8,
    name: "Beryl Security",
    legalName: "Công ty TNHH An ninh mạng Beryl",
    logo: "BS",
    industry: "An toàn thông tin",
    size: "50–100 NV",
    city: "Hà Nội",
    tagline: "Kiểm thử xâm nhập và giám sát SOC cho ngân hàng.",
    about:
      "Beryl Security quy tụ các chuyên gia pentest và phân tích mã độc, cung cấp dịch vụ đánh giá bảo mật định kỳ và trung tâm điều hành an ninh mạng 24/7.",
    perks: [
      "Tài trợ 100% lệ phí thi OSCP, CISSP, CEH.",
      "Thưởng bug bounty nội bộ và nghiên cứu lỗ hổng.",
      "Trang bị MacBook Pro theo cấu hình chuyên môn.",
    ],
    skills: ["Python", "Go", "Linux", "Kubernetes", "SIEM"],
    founded: 2020,
    website: "berylsec.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Theo lịch dự án kiểm thử",
    address: "Tầng 11, toà Peakview, 36 Hoàng Cầu, Đống Đa, Hà Nội",
    workMode: "Service & Product",
    openJobsCount: 5,
    status: "ACTIVE",
    submittedAt: "2026-11-10T13:50:00",
    submittedBy: "Ngô Thành Đạt (dat.ngo@berylsec.vn)",
    taxCode: "0109112233",
    email: "hr@berylsec.vn",
    phone: "024 3514 8899",
    rejectReason: null,
    licenseFile: { name: "GPKD_BerylSecurity.pdf", meta: "2 trang · 1,3 MB" },
  },
  {
    id: 9,
    name: "Sông Hàn Digital",
    legalName: "Công ty Cổ phần Giải pháp Số Sông Hàn",
    logo: "SH",
    industry: "Outsourcing",
    size: "300–500 NV",
    city: "Đà Nẵng",
    tagline: "Đối tác chuyển đổi số cho doanh nghiệp châu Âu và Úc.",
    about:
      "Sông Hàn Digital chuyên thiết kế hệ thống web, di động và dữ liệu đám mây cho khách hàng tại Đức, Thuỵ Sĩ và Úc với đội ngũ Scrum giao tiếp tiếng Anh trực tiếp.",
    perks: [
      "Lớp tiếng Anh giao tiếp công việc miễn phí tại công ty.",
      "15 ngày phép năm, thưởng cuối năm tối thiểu 1 tháng lương.",
      "Văn phòng view sông Hàn, khu vực pantry đầy đủ.",
    ],
    skills: ["TypeScript", "ReactJS", "Node.js", "AWS", ".NET"],
    founded: 2017,
    website: "songhandigital.com",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 7, toà VNPT, 346 Đường 2/9, Hải Châu, Đà Nẵng",
    workMode: "Outsourcing",
    openJobsCount: 11,
    status: "ACTIVE",
    submittedAt: "2026-11-12T10:05:00",
    submittedBy: "Phan Thảo Vy (vy.phan@songhandigital.com)",
    taxCode: "0401765432",
    email: "jobs@songhandigital.com",
    phone: "0236 365 9911",
    rejectReason: null,
    licenseFile: { name: "GPKD_SongHanDigital.pdf", meta: "3 trang · 2,0 MB" },
  },
  {
    id: 10,
    name: "FinBox Labs",
    legalName: "Công ty TNHH Công nghệ FinBox Labs",
    logo: "FB",
    industry: "Dữ liệu & AI",
    size: "50–100 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Chấm điểm tín dụng và phát hiện gian lận bằng AI.",
    about:
      "FinBox Labs xây dựng mô hình học máy giải thích được cho bài toán thẩm định tín dụng và phát hiện giao dịch bất thường tại các ngân hàng số.",
    perks: [
      "Làm việc trực tiếp với chuyên gia AI và Data Science.",
      "Cấp GPU workstation và ngân sách cloud thử nghiệm.",
      "Nghỉ thứ 6 đầu tiên mỗi tháng để tự nghiên cứu.",
    ],
    skills: ["Python", "PyTorch", "FastAPI", "PostgreSQL", "Docker"],
    founded: 2022,
    website: "finboxlabs.ai",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 5, toà Opal, 92 Nguyễn Hữu Cảnh, Bình Thạnh, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 4,
    status: "ACTIVE",
    submittedAt: "2026-11-15T15:25:00",
    submittedBy: "Bùi Quang Vinh (vinh.bui@finboxlabs.ai)",
    taxCode: "0317223344",
    email: "talent@finboxlabs.ai",
    phone: "028 6255 1020",
    rejectReason: null,
    licenseFile: { name: "GPKD_FinBoxLabs.pdf", meta: "2 trang · 1,1 MB" },
  },
  {
    id: 11,
    name: "An Tâm InsurTech",
    legalName: "Công ty Cổ phần Công nghệ Bảo hiểm An Tâm",
    logo: "AT",
    industry: "Fintech",
    size: "100–300 NV",
    city: "Hà Nội",
    tagline: "Số hoá quy trình bồi thường và hợp đồng bảo hiểm.",
    about:
      "An Tâm InsurTech cung cấp nền tảng tích hợp API bảo hiểm nhúng cho các sàn thương mại điện tử và ứng dụng gọi xe tại Việt Nam.",
    perks: [
      "Bảo hiểm sức khoẻ toàn diện cho nhân viên và người thân.",
      "Chế độ hybrid 3 ngày tại văn phòng.",
      "Hỗ trợ chi phí đào tạo chuyên môn hàng năm.",
    ],
    skills: ["Java", "Spring Boot", "ReactJS", "Redis", "AWS"],
    founded: 2020,
    website: "antaminsur.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 10, toà Capital Place, 29 Liễu Giai, Ba Đình, Hà Nội",
    workMode: "Product",
    openJobsCount: 7,
    status: "ACTIVE",
    submittedAt: "2026-11-18T11:45:00",
    submittedBy: "Đỗ Khánh Linh (linh.do@antaminsur.vn)",
    taxCode: "0109234567",
    email: "hr@antaminsur.vn",
    phone: "024 3999 7788",
    rejectReason: null,
    licenseFile: { name: "GPKD_AnTamInsurTech.pdf", meta: "2 trang · 1,5 MB" },
  },
  {
    id: 12,
    name: "Helios Data",
    legalName: "Công ty TNHH Hệ thống Dữ liệu Helios",
    logo: "HD",
    industry: "Hạ tầng đám mây",
    size: "50–100 NV",
    city: "Remote",
    tagline: "Nền tảng kho dữ liệu và BI tự phục vụ cho SME.",
    about:
      "Helios Data phát triển công cụ kết nối dữ liệu đa nguồn giúp đội ngũ vận hành tạo báo cáo trực quan chỉ trong vài phút mà không cần viết SQL phức tạp.",
    perks: [
      "Remote 100%, gặp mặt team-building 2 lần/năm.",
      "Lương gross cạnh tranh, đóng BHXH full lương.",
      "Trợ cấp internet và không gian làm việc.",
    ],
    skills: ["TypeScript", "Python", "ClickHouse", "ReactJS", "Kubernetes"],
    founded: 2021,
    website: "heliosdata.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "65 Lê Lợi, Quận 1, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 3,
    status: "ACTIVE",
    submittedAt: "2026-11-19T16:10:00",
    submittedBy: "Tạ Đức Mạnh (manh.ta@heliosdata.vn)",
    taxCode: "0316998877",
    email: "careers@heliosdata.vn",
    phone: "028 3821 9090",
    rejectReason: null,
    licenseFile: { name: "GPKD_HeliosData.pdf", meta: "2 trang · 1,2 MB" },
  },
  {
    id: 13,
    name: "Verdant Health",
    legalName: "Công ty TNHH Verdant Health",
    logo: "VH",
    industry: "Y tế số",
    size: "50–100 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Phần mềm quản lý phòng khám và hồ sơ bệnh án điện tử.",
    about:
      "Phần mềm quản lý phòng khám, lịch hẹn và hồ sơ bệnh án điện tử cho phòng khám tư nhân.",
    perks: [
      "Gói khám sức khoẻ tổng quát miễn phí hàng năm.",
      "Giờ làm việc linh hoạt, văn phòng ngay trung tâm Quận 1.",
    ],
    skills: ["Node.js", "React", "FHIR", "PostgreSQL"],
    founded: 2022,
    website: "verdanthealth.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "12 Lê Lợi, Quận 1, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 3,
    status: "PENDING",
    submittedAt: "2026-11-24T09:30:00",
    submittedBy: "Lâm Quốc Bảo (bao.lam@verdanthealth.vn)",
    taxCode: "0318765432",
    email: "contact@verdanthealth.vn",
    phone: "028 3920 1122",
    rejectReason: null,
    licenseFile: { name: "GPKD_VerdantHealth.pdf", meta: "2 trang · 1,8 MB" },
  },
  {
    id: 14,
    name: "Kestrel Logistics",
    legalName: "Công ty Cổ phần Công nghệ Logistics Kestrel",
    logo: "KL",
    industry: "Logistics",
    size: "300–500 NV",
    city: "Hà Nội",
    tagline: "Tối ưu tuyến giao hàng chặng cuối.",
    about:
      "Kestrel Logistics xây dựng nền tảng điều phối đội xe, tối ưu lộ trình giao hàng chặng cuối và theo dõi kho bãi thời gian thực cho doanh nghiệp bán lẻ.",
    perks: [
      "Thưởng KPI quý và tháng lương 13.",
      "Phụ cấp ăn trưa và gửi xe tại toà nhà.",
    ],
    skills: ["Java", "Flutter", "PostgreSQL", "Kafka"],
    founded: 2019,
    website: "kestrellogistics.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Hiếm khi",
    address: "Tầng 14, toà Geleximco, 36 Hoàng Cầu, Đống Đa, Hà Nội",
    workMode: "Product",
    openJobsCount: 7,
    status: "PENDING",
    submittedAt: "2026-11-23T16:20:00",
    submittedBy: "Nguyễn Hải Đăng (dang.nguyen@kestrellogistics.vn)",
    taxCode: "0108877665",
    email: "hr@kestrellogistics.vn",
    phone: "024 3772 8899",
    rejectReason: null,
    licenseFile: { name: "GPKD_KestrelLogistics.pdf", meta: "3 trang · 2,4 MB" },
  },
  {
    id: 15,
    name: "Pebble EdTech",
    legalName: "Công ty TNHH Công nghệ Giáo dục Pebble",
    logo: "PE",
    industry: "Giáo dục",
    size: "50–100 NV",
    city: "Đà Nẵng",
    tagline: "Nền tảng học lập trình cho học sinh.",
    about:
      "Pebble EdTech thiết kế môi trường học lập trình tương tác trực tiếp trên trình duyệt kèm hệ thống chấm bài tự động cho học sinh phổ thông.",
    perks: [
      "Nghỉ hè công ty 4 ngày và ngân sách mua sách.",
      "Môi trường trẻ trung, thân thiện.",
    ],
    skills: ["Vue", "Laravel", "MySQL", "Docker"],
    founded: 2021,
    website: "pebbleedtech.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "45 Trần Phú, Hải Châu, Đà Nẵng",
    workMode: "Product",
    openJobsCount: 2,
    status: "PENDING",
    submittedAt: "2026-11-23T11:05:00",
    submittedBy: "Trương Ngọc Mai (mai.truong@pebbleedtech.vn)",
    taxCode: "0402011223",
    email: "hello@pebbleedtech.vn",
    phone: "0236 391 2233",
    rejectReason: null,
    licenseFile: { name: "GPKD_PebbleEdTech.pdf", meta: "2 trang · 1,1 MB" },
  },
  {
    id: 16,
    name: "Aqua Robotics",
    legalName: "Công ty Cổ phần Tự động hoá Aqua Robotics",
    logo: "AQ",
    industry: "IoT",
    size: "50–100 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Cảm biến IoT giám sát chất lượng nước nuôi trồng thuỷ sản.",
    about:
      "Aqua Robotics phát triển thiết bị cảm biến thông minh và nền tảng phân tích cảnh báo môi trường nước cho các trang trại nuôi tôm công nghệ cao ở Đồng bằng sông Cửu Long.",
    perks: [
      "Hỗ trợ chỗ ở khi công tác thực địa.",
      "Thưởng sáng kiến kỹ thuật và bằng sáng chế.",
    ],
    skills: ["C++", "Python", "MQTT", "ReactJS"],
    founded: 2022,
    website: "aquarobotics.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Lô T2-4, Khu Công nghệ cao, TP. Thủ Đức, TP. Hồ Chí Minh",
    workMode: "Hardware & Software",
    openJobsCount: 4,
    status: "PENDING",
    submittedAt: "2026-11-22T15:10:00",
    submittedBy: "Võ Văn Khoa (khoa.vo@aquarobotics.vn)",
    taxCode: "0317554433",
    email: "hr@aquarobotics.vn",
    phone: "028 3736 5511",
    rejectReason: null,
    licenseFile: { name: "GPKD_AquaRobotics.pdf", meta: "2 trang · 1,9 MB" },
  },
  {
    id: 17,
    name: "Mira Banking Tech",
    legalName: "Công ty TNHH Giải pháp Ngân hàng Mira",
    logo: "MB",
    industry: "Fintech",
    size: "100–300 NV",
    city: "Hà Nội",
    tagline: "Nền tảng ngân hàng lõi mở cho ngân hàng số.",
    about:
      "Mira Banking Tech cung cấp bộ API tài chính mở (Open Banking) và giải pháp eKYC tốc độ cao cho các tổ chức tín dụng.",
    perks: [
      "Gói bảo hiểm nâng cao và thưởng cuối năm 2 tháng.",
      "Phụ cấp ăn trưa 1,2 triệu/tháng.",
    ],
    skills: ["Java", "Spring Boot", "Kafka", "Kubernetes"],
    founded: 2020,
    website: "mirabanking.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không OT",
    address: "Tầng 18, toà Lotte Center, 54 Liễu Giai, Ba Đình, Hà Nội",
    workMode: "Product",
    openJobsCount: 6,
    status: "PENDING",
    submittedAt: "2026-11-21T10:45:00",
    submittedBy: "Phạm Minh Đức (duc.pham@mirabanking.vn)",
    taxCode: "0109001122",
    email: "recruit@mirabanking.vn",
    phone: "024 3333 6677",
    rejectReason: null,
    licenseFile: { name: "GPKD_MiraBankingTech.pdf", meta: "2 trang · 1,5 MB" },
  },
  {
    id: 18,
    name: "ABC Tech",
    legalName: "Công ty TNHH Thương mại Dịch vụ ABC Tech",
    logo: "AB",
    industry: "Outsourcing",
    size: "10–50 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Cung cấp giải pháp nhập liệu và dịch vụ văn phòng.",
    about: "Đơn vị cung cấp nhân sự bán thời gian và hỗ trợ vận hành tổng hợp.",
    perks: ["Làm việc linh hoạt."],
    skills: ["Excel", "Word"],
    founded: 2024,
    website: "abctech-sample.vn",
    workingDays: "Thứ 2 – Thứ 7",
    overtime: "Theo ca",
    address: "88 Cộng Hoà, Tân Bình, TP. Hồ Chí Minh",
    workMode: "Service",
    openJobsCount: 0,
    status: "REJECTED",
    submittedAt: "2026-11-20T14:00:00",
    submittedBy: "Trần Văn C (c.tran@abctech-sample.vn)",
    taxCode: "0318990011",
    email: "info@abctech-sample.vn",
    phone: "028 3811 0099",
    rejectReason: "Giấy phép kinh doanh không rõ nét và ngành nghề đăng ký không phù hợp lĩnh vực CNTT.",
    licenseFile: { name: "GPKD_ABCTech.pdf", meta: "1 trang · 0,4 MB" },
  },
  {
    id: 19,
    name: "Nova Trading Tech",
    legalName: "Công ty TNHH Nova Trading Tech",
    logo: "NT",
    industry: "Thương mại điện tử",
    size: "10–50 NV",
    city: "Hà Nội",
    tagline: "Phân phối thiết bị và phần mềm bán hàng.",
    about: "Kinh doanh thiết bị POS và phần mềm quản lý cửa hàng nhỏ.",
    perks: ["Hoa hồng theo doanh số."],
    skills: ["PHP", "MySQL"],
    founded: 2023,
    website: "novatrading.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không",
    address: "19 Nguyễn Trãi, Thanh Xuân, Hà Nội",
    workMode: "Service",
    openJobsCount: 0,
    status: "REJECTED",
    submittedAt: "2026-11-18T08:50:00",
    submittedBy: "Lê Minh (minh.le@novatrading.vn)",
    taxCode: "0109998811",
    email: "contact@novatrading.vn",
    phone: "024 3555 0011",
    rejectReason: "Mã số thuế trên hồ sơ không khớp với bản scan giấy phép kinh doanh đính kèm.",
    licenseFile: { name: "GPKD_NovaTrading.pdf", meta: "1 trang · 0,7 MB" },
  },
  {
    id: 20,
    name: "FastCash VN",
    legalName: "Công ty TNHH Công nghệ FastCash Việt Nam",
    logo: "FC",
    industry: "Fintech",
    size: "50–100 NV",
    city: "TP. Hồ Chí Minh",
    tagline: "Ứng dụng hỗ trợ tài chính tiêu dùng nhanh.",
    about: "Phát triển ứng dụng di động kết nối khoản vay ngắn hạn.",
    perks: ["Thưởng theo quý."],
    skills: ["React Native", "Node.js"],
    founded: 2022,
    website: "fastcash-demo.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Có",
    address: "210 Điện Biên Phủ, Quận 3, TP. Hồ Chí Minh",
    workMode: "Product",
    openJobsCount: 0,
    status: "LOCKED",
    submittedAt: "2026-10-01T10:00:00",
    submittedBy: "Phạm Huy (huy.pham@fastcash-demo.vn)",
    taxCode: "0317001199",
    email: "hr@fastcash-demo.vn",
    phone: "028 3932 9988",
    rejectReason: "Tạm khoá do đăng nhiều tin tuyển dụng có dấu hiệu thu phí ứng viên trái quy định.",
    licenseFile: { name: "GPKD_FastCashVN.pdf", meta: "2 trang · 1,3 MB" },
  },
  {
    id: 21,
    name: "BitMax Solutions",
    legalName: "Công ty TNHH Giải pháp BitMax",
    logo: "BM",
    industry: "Outsourcing",
    size: "10–50 NV",
    city: "Đà Nẵng",
    tagline: "Gia công ứng dụng web và blockchain.",
    about: "Phát triển smart contract và cổng web theo hợp đồng.",
    perks: ["Làm việc linh hoạt."],
    skills: ["Solidity", "Node.js", "ReactJS"],
    founded: 2023,
    website: "bitmax-sol.vn",
    workingDays: "Thứ 2 – Thứ 6",
    overtime: "Không",
    address: "110 Nguyễn Văn Linh, Thanh Khê, Đà Nẵng",
    workMode: "Outsourcing",
    openJobsCount: 0,
    status: "LOCKED",
    submittedAt: "2026-10-09T14:20:00",
    submittedBy: "Hoàng Tuấn (tuan.hoang@bitmax-sol.vn)",
    taxCode: "0402123456",
    email: "hr@bitmax-sol.vn",
    phone: "0236 377 1122",
    rejectReason: "Doanh nghiệp tạm ngừng hoạt động theo thông báo từ người đại diện pháp luật.",
    licenseFile: { name: "GPKD_BitMax.pdf", meta: "2 trang · 1,0 MB" },
  },
];

function findCompanyIndex(id: number): number {
  return COMPANIES.findIndex((c) => c.id === id);
}

export async function listCompanies(filter?: CompanyListFilter): Promise<CompanyDto[]> {
  const needle = filter?.q?.trim().toLowerCase() ?? "";
  const city = filter?.city && filter.city !== "all" ? filter.city : "";
  const industry = filter?.industry && filter.industry !== "all" ? filter.industry : "";
  const status = filter?.status && filter.status !== "ALL" ? filter.status : "";

  const out = COMPANIES.filter((c) => {
    if (status && c.status !== status) return false;
    if (city && c.city !== city) return false;
    if (industry && c.industry !== industry) return false;
    if (needle) {
      const hay = `${c.name} ${c.legalName} ${c.taxCode} ${c.tagline} ${c.skills.join(" ")}`.toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    return true;
  });

  return mockResolve(out);
}

export async function getCompany(id: number): Promise<CompanyDto> {
  const found = COMPANIES.find((c) => c.id === id);
  if (!found) {
    return mockReject("Không tìm thấy thông tin công ty.");
  }
  return mockResolve(found);
}

export async function approveCompany(id: number): Promise<CompanyDto> {
  const idx = findCompanyIndex(id);
  if (idx === -1) return mockReject("Không tìm thấy công ty.");
  const target = COMPANIES[idx];
  if (target.status !== "PENDING") {
    return mockReject("Công ty này đã được xử lý trước đó. Vui lòng tải lại danh sách.");
  }
  target.status = "ACTIVE";
  target.rejectReason = null;
  return mockResolve(target);
}

export async function rejectCompany(id: number, reason: string): Promise<CompanyDto> {
  const trimmed = reason.trim();
  if (!trimmed) {
    return mockReject("Vui lòng nhập lý do từ chối.");
  }
  const idx = findCompanyIndex(id);
  if (idx === -1) return mockReject("Không tìm thấy công ty.");
  const target = COMPANIES[idx];
  if (target.status !== "PENDING") {
    return mockReject("Công ty này đã được xử lý trước đó. Vui lòng tải lại danh sách.");
  }
  target.status = "REJECTED";
  target.rejectReason = trimmed;
  return mockResolve(target);
}

export async function lockCompany(id: number, reason?: string): Promise<CompanyDto> {
  const idx = findCompanyIndex(id);
  if (idx === -1) return mockReject("Không tìm thấy công ty.");
  const target = COMPANIES[idx];
  if (target.status !== "ACTIVE") {
    return mockReject("Chỉ có thể khoá công ty đang hoạt động.");
  }
  target.status = "LOCKED";
  target.rejectReason = reason?.trim() || "Bị khoá bởi quản trị viên.";
  return mockResolve(target);
}

export async function unlockCompany(id: number): Promise<CompanyDto> {
  const idx = findCompanyIndex(id);
  if (idx === -1) return mockReject("Không tìm thấy công ty.");
  const target = COMPANIES[idx];
  if (target.status !== "LOCKED") {
    return mockReject("Công ty hiện không ở trạng thái bị khoá.");
  }
  target.status = "ACTIVE";
  target.rejectReason = null;
  return mockResolve(target);
}
