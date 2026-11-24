"""Cấu hình pipeline KB1. Đường dẫn tính từ vị trí file này."""
import pathlib

from shared.config import ROLE_GROUPS

ROOT = pathlib.Path(__file__).resolve().parents[2]   # build_kb/
KB1 = ROOT / "kb1"
PDF_DIR = KB1 / "data" / "pdf"
SOURCES_CSV = KB1 / "data" / "sources.csv"
OUT = KB1 / "out"

# file -> (loại, [nhóm vai trò]). role: sinh USED_IN; topic, out: chỉ đóng góp kỹ năng và nhóm.
ROADMAPS = {
    "backend": ("role", ["Backend"]),
    "frontend": ("role", ["Frontend"]),
    "full-stack": ("role", ["Fullstack"]),
    "android": ("role", ["Mobile"]),
    "devops": ("role", ["DevOps"]),
    "devsecops": ("role", ["DevOps", "Security"]),
    "cyber-security": ("role", ["Security"]),
    "qa": ("role", ["QA"]),
    "data-engineer": ("role", ["Data"]),
    "data-analyst": ("role", ["Data"]),
    "mlops": ("role", ["AI/ML"]),
    "ai-engineer": ("role", ["AI/ML"]),
    "software-architect": ("topic", []),
    "api-design": ("topic", []),
    "cloud-computing": ("topic", []),
    "network-engineer": ("role", ["IT Support"]),   # nhóm mới từ KB3 (21/11/2026)
    "game-developer": ("role", ["Game"]),
    "ux-design": ("role", ["Design"]),
}

# --- Màu ô, đo ở Bước 1 trên cả 18 PDF (giá trị fill làm tròn 2 chữ số) ---
MAIN_FILLS = {(0.99, 1.0, 0.0)}                     # vàng: chủ đề chính
LINE_FILLS = {(0.16, 0.47, 0.89), (0.17, 0.47, 0.89)}   # xanh dương: đường nối, và ô trên luồng
SUB_FILLS = {
    (1.0, 0.9, 0.6),                                # kem: chủ đề con
    (0.96, 0.96, 0.96), (0.9, 0.9, 0.9),            # xám nhạt: mục con cấp 3
} | LINE_FILLS                                      # ô xanh: lọc thêm bằng NOISE_PATTERNS
CONTAINER_FILLS = {(1.0, 1.0, 1.0)}                 # trắng viền đen: khung nhóm, hoặc khung chú thích
LINK_FILLS = {
    (0.25, 0.21, 0.84), (0.25, 0.21, 0.83),         # tím: liên kết sang roadmap khác, quảng cáo
    (0.82, 0.82, 0.82), (0.87, 0.87, 0.87),         # xám: liên kết
    (0.89, 0.89, 0.89), (0.92, 0.92, 0.92),         # xám: roadmap.sh, ghi chú
    (0.14, 0.14, 0.14), (0.2, 0.2, 0.2),            # đen: "Visit...", "Checkpoint..."
    (0.99, 1.0, 0.62),                              # vàng nhạt: "Python Roadmap"
}

# --- Ngưỡng hình học (đơn vị PDF) ---
MIN_BOX_W, MIN_BOX_H = 12, 8        # nhỏ hơn: dấu chấm, ô chú giải
MIN_FRAME_W, MIN_FRAME_H = 60, 40   # khung chỉ có viền, không có nền
MAX_PAGE_SHARE = 0.6                # ô chiếm hơn tỉ lệ này của trang: nền, không phải ô
SECTION_SIZE_RATIO = 1.15           # cỡ chữ / trung vị: tiêu đề phần
CLUSTER_GAP = 8                     # các ô cách nhau ít hơn: cùng một chồng ô
HEADING_GAP = 14                    # chữ rời cách chồng ô ít hơn: tiêu đề của chồng ô
CONNECTOR_GAP = 8                   # đầu đường nối cách ô ít hơn: đường nối chạm ô
MAX_DIST = 150                      # xa ô chính hơn: orphan

PICK_ONE_RE = r"pick one|choose one|one of these|^popular"
PROSE_MIN_WORDS = 9                 # chữ rời dài từng này từ trở lên: câu văn, không phải nhãn

NOISE_PATTERNS = [
    r"is offering \d+% off", r"find the detailed version", r"^roadmap\.sh$", r"related roadmaps?",
    r"continue learning", r"check them out", r"pre-?requisites", r"\broadmaps?$",
    r"^visit\b", r"also visit", r"^checkpoint\b", r"^keep learning$",
    r"personal recommendation", r"alternative option", r"order not strict", r"key topics",
    r"^\W*\d+\W*$",
]

# --- Bộ kiểm tay (mục 5.1, 6 của kế hoạch) ---
GOLD_PDFS = {"backend", "ai-engineer"}
GOLD_GROUP_SAMPLE = 50
GOLD_LABEL_SAMPLE = 50
GOLD_SEED = 42

# --- Bước 4: phân loại nhãn ---
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
LLM_BATCH = 50
LLM_MAX_RETRIES = 8                  # Groq giới hạn token/phút: client tự chờ rồi gọi lại
LLM_PARAMS = {"temperature": 0, "reasoning_effort": "low"}   # phân loại nhãn không cần suy luận sâu, đỡ tốn hạn mức
LABEL_TYPES = ("technology", "concept", "category", "not_skill")
NOT_SKILL_PATTERNS = [
    r"^(what|how|why|when|which|who)\b", r"\?$", r"\bconsiderations?\b", r"\bbenefits\b",
    r"\bintroduction\b", r"^basics?\b", r"\bvs\.?\s", r"\busecases?\b", r"\buse cases\b",
    r"\blimitations\b", r"^impact on\b", r"^roles and\b",
]

# --- Bước 5: sinh tri thức ---
# Ngôn ngữ/nền tảng: con là technology dưới các cha này được coi là PARENT_OF
PLATFORM_PARENTS = {
    "java", "javascript", "typescript", "python", "c#", ".net", "kotlin", "php", "ruby", "rust", "go",
    "node.js", "react", "vue.js", "angular", "android", "linux", "docker", "kubernetes",
    "aws", "azure", "gcp", "git", "sql",
}
# Alias dễ nhầm, không dùng để khớp tự động (Knowledge base.md, mục 4)
AMBIGUOUS_ALIASES = {"go", "c", "r", "spring"}

# --- Alias từ tag synonyms của Stack Overflow (so_aliases.py) ---
SO_SYNONYMS_CSV = KB1 / "data" / "tag_synonyms.csv"
SO_REPORT_CSV = OUT / "so_alias_report.csv"
# Từ không làm đổi nghĩa tên: "apache-solr" = "solr", "go-language" = "go"
SO_FILLER_TOKENS = {"amazon", "aws", "apache", "google", "microsoft", "ms", "language", "lang", "framework"}
# Tag đích của SO khác tên trong KB: tag đích -> key của Skill. Duyệt tay, vì khớp tự động qua tag
# đồng nghĩa sẽ nhầm ("base" -> radix, "man" -> manpage, "xp" -> windows-xp).
SO_BRIDGE = {
    ".net": ".net framework", "admob": "google admob", "amazon-dynamodb": "dynamodb", "amazon-eks": "aws eks",
    "amazon-neptune": "aws neptune", "amazon-s3": "s3", "amazon-sagemaker": "aws sagemaker", "amazon-ses": "ses",
    "amazon-sns": "aws sns", "amazon-sqs": "aws sqs", "amazon-web-services": "aws",
    "android-espresso": "espresso", "android-jetpack-compose": "jetpack compose", "android-livedata": "livedata",
    "apache-flink": "flink", "aws-cloudformation": "cloudformation", "azure-virtual-machine": "azure vm",
    "chef-infra": "chef", "dagger-hilt": "hilt", "envoyproxy": "envoy", "google-cloud-firestore": "firestore",
    "google-cloud-platform": "gcp", "grafana-loki": "loki", "idempotent": "idempotency",
    "ionic-framework": "ionic", "jestjs": "jest", "memory-leaks": "memory leak",
    "model-view-controller": "mvc", "nlp": "natural language processing", "reactjs": "react",
    "recurrent-neural-network": "rnn", "selenium-webdriver": "selenium", "single-sign-on": "sso",
    "snowflake-cloud-data-platform": "snowflake", "virtual-machine": "vm", "web-applications": "web application",
}
# Tên gọi khác đã duyệt tay, không suy ra được từ cách viết
SO_KEEP = {
    "802.11", "11ty", "a11y", "k8s", "oauth2",
    "azure-sql", "azure-sql-server", "azure-storage-blobs", "bigquery", "cdk", "gcs", "google-storage",
    "sql-azure", "visual-studio-team-services", "vsts", "windows-azure", "windows-azure-blob", "zeit",
    "c-sharp", "cpp", "csharp", "cxx", "core-java", "ecmascript", "golang", "java-se", "rstats",
    "vanilla-javascript", "vanilla-js", "vanillajs", "windows-powershell", "js",
    "mongo", "memcache", "mssql", "pgsql", "postgres", "sqllite",
    "apple-metal", "cypressio", "ggplot", "httpd", "lesscss", "openai", "scss", "travis",
    "cascading-style-sheet", "hypertext-preprocessor", "macosx", "osx",
    "rest-api", "restapi", "restful", "restful-architecture", "restful-web-services",
    "model-view-presenter", "model-view-viewmodel", "object-orientation", "object-oriented",
    "object-oriented-design", "ood", "oops", "test-driven", "testdrivendesign", "testdrivendevelopment",
    "cross-site-scripting", "xsrf", "json-web-token", "elk-stack", "software-as-a-service",
    "infrastructure-as-a-code", "data-warehousing", "batch-process", "load-balance", "fine-tune", "tts",
    "parallel-computing", "parallel-programming", "parallelism", "software-architecture", "software-testing",
    "revision-control", "source-code-control", "source-code-management", "source-control", "vcs",
    "cloud-firestore", "dot-net", "dotnet", "firebase-firestore", "android-compose", "webapp", "webapps",
    "authorisation", "loadtest", "normalisation", "ratelimit", "salesforce.com", "unittest",
}
# Đúng nghĩa nhưng là từ thường hoặc quá ngắn: ghi vào ambiguous_aliases, không khớp tự động
SO_AMBIGUOUS = {
    "auth", "az", "bq", "cache", "db", "di", "elastic", "functional", "index", "indexes", "mac", "oo", "os",
    "parallel", "pattern", "patterns", "plt", "py", "scm", "test", "tests",
}
