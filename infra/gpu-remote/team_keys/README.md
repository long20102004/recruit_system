# SSH public key của thành viên

Mỗi người muốn SSH vào máy GPU thuê thì thêm **khóa công khai** của mình vào thư mục này,
đặt tên `<ten>.pub` (ví dụ `long.pub`), nội dung là một dòng `ssh-ed25519 AAAA... ghi-chu`.

- Chỉ commit file `.pub`. **Không bao giờ** commit khóa bí mật (`id_ed25519` không có đuôi `.pub`).
- `setup.sh` tự cài tất cả key ở đây lên máy GPU mỗi lần setup.
- Cài key ngay khi máy đang chạy: `./infra/gpu-remote/setup.sh <host> <port> --keys-only`.
