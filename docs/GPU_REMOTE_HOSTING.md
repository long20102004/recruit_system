# Host 3 service AI trên máy GPU thuê

Hướng dẫn chạy `interview-ai`, `cv-extraction-ai` và `cvmatch-ai` trên một máy GPU thuê theo giờ.
Backend Java, MySQL, frontend **và mọi database (kể cả Postgres của cvmatch)** chạy trên máy local;
máy GPU chỉ tính toán, không giữ dữ liệu. Phạm vi: dùng cho đồ án (test, demo), không phải production.

```
 Máy local                                        Máy GPU thuê (Ubuntu + Docker + RTX 3090)
 ┌───────────────────────────┐  HTTP (URL public) ┌─────────────────────────────────────────┐
 │ backend Java (8081-8083)  │ ─────────────────▶ │ :42000 interview-ai     (BERT, CPU)     │
 │ MySQL, Redis, frontend    │                    │ :42001 cv-extraction-ai (Qwen3, GPU)    │
 │ cvmatch-db 127.0.0.1:5433 │ ◀── reverse SSH ── │ :42003 cvmatch-ai       (bge-m3, GPU)   │
 └───────────────────────────┘   tunnel (DB)      │   DB = docker0:15433 ─▶ tunnel ─▶ local │
                                                  └─────────────────────────────────────────┘
```

cvmatch-ai đọc/ghi DB qua **reverse SSH tunnel** do [db-tunnel.sh](../infra/gpu-remote/db-tunnel.sh)
mở từ máy local. Tunnel chỉ bind trên mạng Docker nội bộ của máy GPU, không public Internet.
Hệ quả: **máy local phải bật và tunnel phải chạy** thì cvmatch-ai mới hoạt động; mỗi truy vấn DB
đi qua mạng nên matching chậm hơn một chút so với DB đặt cùng máy.

Các file liên quan:

| File | Vai trò |
|---|---|
| [infra/gpu-remote/setup.sh](../infra/gpu-remote/setup.sh) | Script dựng lại toàn bộ từ máy trống, chạy trên máy local |
| [infra/gpu-remote/db-tunnel.sh](../infra/gpu-remote/db-tunnel.sh) | Reverse SSH tunnel để cvmatch-ai dùng Postgres ở local (`start`/`stop`/`status`) |
| [infra/gpu-remote/docker-compose.remote.yml](../infra/gpu-remote/docker-compose.remote.yml) | Override mở 3 cổng public (42000/42001/42003), trỏ DB cvmatch về tunnel, bật tối ưu llama.cpp |
| [infra/gpu-remote/team_keys/](../infra/gpu-remote/team_keys/) | SSH public key của thành viên được phép vào máy |
| [docker-compose.gpu.yml](../docker-compose.gpu.yml) | Bật GPU cho cv-extraction-ai và cvmatch-ai |

## 1. Thuê máy

Gói đang dùng: **RTX 3090 · Standard** (24GB VRAM, 25 nhân, 55GB RAM), khoảng 15.000đ/giờ.

Khi thuê:

- Hệ điều hành: **Ubuntu 24.04 AI** (đã có driver NVIDIA, Docker và NVIDIA runtime).
- Tích **Sử dụng SSH key**, dán nội dung `~/.ssh/id_ed25519.pub`. Chưa có key thì tạo:
  `ssh-keygen -t ed25519 -C "gpu-do-an"`.
- Không cần IP tĩnh.

Sau khi máy chạy, trang quản lý hiện **lệnh SSH** (ví dụ `ssh -p 20121 root@hn1.forai.cloud`)
và **dải cổng riêng** (ví dụ `42000-42999`). Ghi lại host, cổng SSH và cổng đầu của dải.

> Nhà cung cấp **xóa toàn bộ dữ liệu khi tắt máy**. Mỗi lần thuê lại là một máy trống,
> nên luôn dựng lại bằng `setup.sh` (bước 2).

## 2. Dựng 3 service bằng một lệnh

Điều kiện trên máy local:

- File `.env` ở gốc repo có `SERVICE_TOKEN`, `CVMATCH_HMAC_KEY` (giá trị phải giống backend đang dùng)
  và `STORAGE_ROOT` (thư mục chứa dữ liệu DB ở local).
- Docker chạy được ở local (script tự bật `cvmatch-db` local).
- Có file model `model-v4-q4_k_m.gguf` trong `ai-service/extraction/merged_model/`
  hoặc `ai-service/models/cv-extraction/`.
- Có KB snapshot trong `ai-service/matching/kb-builder/out/snapshot/`.

Chạy từ gốc repo:

```bash
./infra/gpu-remote/setup.sh hn1.forai.cloud 20121
# dải cổng khác 42000:     --port-base 43000
# GPU khác RTX 3090/A4000: --cuda-arch 89   (L4/4090 = 89, T4 = 75, A100 = 80)
```

Script lần lượt: xóa host key cũ, kiểm tra SSH, cài key của thành viên, bật `cvmatch-db` ở local,
kiểm tra GPU/Docker (tự cài nếu thiếu), đồng bộ `ai-service` và model (~1,2GB), ghi `.env` trên máy GPU,
build image, mở reverse tunnel DB, khởi động 3 service (không chạy DB trên máy GPU), chờ `/health`
rồi in ra URL.

Thời gian: lần đầu khoảng **15–25 phút** (build llama.cpp CUDA, tải bge-m3 ~2,3GB và BERT ~700MB).

Kết thúc, script in ra:

```
AI_URL=http://hn1.forai.cloud:42000
CV_EXTRACTION_URL=http://hn1.forai.cloud:42001
CVMATCH_URL=http://hn1.forai.cloud:42003
```

## 3. Trỏ backend local sang máy GPU

Dán 3 dòng trên vào `.env` ở gốc repo (ghi đè giá trị cũ), rồi khởi động lại các service Java:

- Chạy bằng Docker: `docker compose up -d identity-service recruitment-service interview-service`
- Chạy Java trực tiếp: export 3 biến trên rồi chạy lại ứng dụng.

Kiểm tra nhanh:

```bash
curl http://hn1.forai.cloud:42000/health
curl http://hn1.forai.cloud:42001/health
curl http://hn1.forai.cloud:42003/health
```

**Cách thay thế: SSH tunnel.** Không cần URL public, backend gọi `localhost` như khi chạy local:

```bash
ssh -p 20121 -N -L 8000:127.0.0.1:8000 -L 8001:127.0.0.1:8001 -L 8003:127.0.0.1:8003 root@hn1.forai.cloud
```

Khi đó dùng `AI_URL=http://localhost:8000`, `CV_EXTRACTION_URL=http://localhost:8001`,
`CVMATCH_URL=http://localhost:8003` (backend chạy trong Docker thì thay `localhost` bằng `host.docker.internal`).

## 4. Dùng hằng ngày

| Việc | Lệnh |
|---|---|
| Thuê lại máy mới | Thuê trên web, chạy `./infra/gpu-remote/setup.sh <host> <ssh-port>` |
| Máy vẫn đang chạy, chỉ cập nhật code AI | `./infra/gpu-remote/setup.sh <host> <ssh-port>` (Docker dùng lại cache, nhanh hơn) |
| Xem trạng thái | `ssh -p <port> root@<host> 'cd /root/recruit_system && docker compose ps'` |
| Xem log 1 service | `ssh -p <port> root@<host> 'cd /root/recruit_system && docker compose logs --tail 100 cv-extraction-ai'` |
| Xem GPU | `ssh -p <port> root@<host> nvidia-smi` |
| Kiểm tra tunnel DB | `./infra/gpu-remote/db-tunnel.sh <host> <ssh-port> status` |
| Bật lại tunnel DB (sau khi máy local ngủ/khởi động lại) | `./infra/gpu-remote/db-tunnel.sh <host> <ssh-port> start` |
| Xong việc | `./infra/gpu-remote/db-tunnel.sh <host> <ssh-port> stop`, rồi **tắt máy trên trang quản lý** để ngừng tính tiền |

Chi phí tham khảo: 15.000đ/giờ → một buổi 4 tiếng khoảng 60.000đ. Ngày bảo vệ nên thuê trước
vài tiếng và chạy `setup.sh` sớm, không tắt máy giữa chừng.

## 5. Cho người khác dùng

Có ba mức, chọn mức thấp nhất đủ dùng.

### Mức 1: chỉ gọi API (thường là đủ)

Gửi cho thành viên 3 dòng URL ở bước 2, kèm `SERVICE_TOKEN` (cvmatch-ai kiểm tra token này).
Họ dán vào `.env` local của họ và chạy backend như bình thường. Không cần SSH.

### Mức 2: SSH vào máy GPU (xem log, restart, chạy `setup.sh`)

1. Thành viên tạo key trên máy họ: `ssh-keygen -t ed25519 -C "<ten>"`.
2. Họ gửi file **`~/.ssh/id_ed25519.pub`** (khóa công khai, gửi được qua chat).
   Tuyệt đối không gửi file `id_ed25519` (khóa bí mật).
3. Lưu thành `infra/gpu-remote/team_keys/<ten>.pub` và commit.
4. Cài key:
   - Máy đang chạy: `./infra/gpu-remote/setup.sh <host> <ssh-port> --keys-only`.
   - Lần thuê sau: `setup.sh` tự cài.
5. Thành viên đăng nhập: `ssh -p <ssh-port> root@<host>`.

Gỡ quyền: xóa file `.pub` khỏi `team_keys/`, rồi trên máy GPU xóa dòng tương ứng trong
`/root/.ssh/authorized_keys` (hoặc đợi lần thuê lại, máy mới sẽ không còn key đó).

Lưu ý: ai có SSH là có quyền **root** trên máy, chỉ cấp cho người trong nhóm.

### Mức 3: tự chạy `setup.sh` từ máy của họ

Ngoài mức 2, người đó cần: repo mới nhất, file `.env` có `SERVICE_TOKEN` và `CVMATCH_HMAC_KEY`
giống của nhóm, file `model-v4-q4_k_m.gguf` và KB snapshot. Gửi model và `.env` qua kênh riêng
(Drive nội bộ), **không commit** vào Git.

Không chia sẻ tài khoản và mật khẩu trang thuê GPU; người giữ tài khoản bật/tắt máy và trả tiền.

## 6. Bảo mật (mức đồ án)

- `cv-extraction-ai` và `interview-ai` **không có xác thực**. Ai biết URL public đều gọi được
  khi máy đang bật. Chấp nhận được cho đồ án vì máy chỉ bật lúc dùng; không đăng URL lên chỗ công khai.
  Cần chặt hơn thì dùng SSH tunnel (bước 3) và bỏ các mục `ports` trong `docker-compose.remote.yml`.
- Postgres của cvmatch chỉ nằm ở máy local; tắt máy GPU không làm mất dữ liệu CV/match.
- Dữ liệu đi qua URL public là HTTP thường, không mã hóa. Chỉ dùng CV mẫu khi test.
- `setup.sh` xóa host key cũ mỗi lần chạy (vì mỗi lần thuê là máy mới), nên SSH sẽ không cảnh báo nếu
  host bị giả mạo. Chỉ chạy với host lấy từ trang quản lý.

## 7. Xử lý sự cố

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `Host key verification failed` | Chưa gõ `yes` khi SSH hỏi. `setup.sh` tự xử lý; chạy tay thì `ssh-keygen -R "[host]:port"` |
| `Permission denied (publickey)` | Key chưa được cài. Chạy `ssh-copy-id -p <port> root@<host>` (nhập mật khẩu trên trang quản lý) |
| cv-extraction build lỗi `unsupported gpu architecture` | Sai `--cuda-arch`. GPU dòng RTX 50xx cần thêm sửa `CUDA_VERSION` ≥ 12.8 trong `ai-service/extraction/Dockerfile.gpu` |
| cvmatch-ai không lên, log báo thiếu HMAC | `CVMATCH_HMAC_KEY` trong `.env` local đang trống |
| cvmatch-ai lỗi kết nối DB / `/health` báo `db` lỗi | Tunnel DB không chạy hoặc `cvmatch-db` local đã tắt: `docker compose --profile match up -d cvmatch-db` rồi `db-tunnel.sh <host> <port> start`; xem log bằng `db-tunnel.sh ... status` |
| `db-tunnel.sh` log báo `remote port forwarding failed` | Cổng 15433 trên máy GPU còn bị phiên cũ giữ; script tự thử lại sau 5s, hoặc chạy lại `setup.sh` |
| cvmatch-ai lâu mới healthy | Lần đầu tải bge-m3 ~2,3GB; healthcheck cho phép tới 10 phút |
| `curl` URL public bị timeout | Dải cổng không phải 42000: chạy lại với `--port-base <cổng đầu>` |
| Backend gọi AI bị 401 ở cvmatch | `SERVICE_TOKEN` của backend khác với trên máy GPU; sửa `.env` local rồi chạy lại `setup.sh` |
