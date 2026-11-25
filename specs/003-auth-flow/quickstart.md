# Quickstart: kiểm chứng luồng xác thực

## Chuẩn bị

```bash
docker compose up -d --build        # có thêm redis và mailpit
cd frontend && npm run dev          # http://localhost:5173
```

- Hộp thư dev (Mailpit): http://localhost:8025
- Redis: `docker compose exec redis redis-cli   (hoặc redis-cli -p 6380)`
- Admin seed: `admin@hirelens.local` / `demo1234`

## Kịch bản

1. **Đăng ký + xác thực (US1)**: đăng ký email mới → màn "kiểm tra email" → Mailpit có mail → bấm link → vào màn chọn vai trò. Đăng nhập trước khi bấm link → báo chưa xác thực, có nút gửi lại.
2. **Khoá tạm (US2)**: đăng nhập sai 5 lần với `candidate@hirelens.local` → lần 6 nhập đúng vẫn báo khoá tạm kèm số phút. `redis-cli TTL auth:login:lock:candidate@hirelens.local` > 0. `redis-cli DEL` key đó → đăng nhập được.
3. **Quên mật khẩu (US3)**: `/forgot-password` → mail có link → đặt mật khẩu mới → token cũ gọi `GET /api/auth/me` trả 401; đăng nhập bằng mật khẩu mới được.
4. **Admin khoá (US4)**, dùng curl qua gateway `:8080`:
   ```bash
   A=$(curl -s localhost:8080/api/auth/login -H 'content-type: application/json' \
       -d '{"email":"admin@hirelens.local","password":"demo1234"}' | jq -r .token)
   C=$(curl -s localhost:8080/api/auth/login -H 'content-type: application/json' \
       -d '{"email":"candidate@hirelens.local","password":"demo1234"}' | jq -r .token)
   curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/cvs/me -H "Authorization: Bearer $C"   # 200/404
   curl -s -X PATCH localhost:8080/api/admin/users/2/lock -H "Authorization: Bearer $A" \
       -H 'content-type: application/json' -d '{"reason":"test"}'
   curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/cvs/me -H "Authorization: Bearer $C"   # 401
   curl -s -X PATCH localhost:8080/api/admin/users/2/unlock -H "Authorization: Bearer $A"
   ```
   Token `$C` cũ vẫn 401 sau khi mở khoá; đăng nhập lại được token mới.
5. **Cache (SC-006)**: gọi API recruitment hai lần với cùng token; `redis-cli HGETALL auth:user:2` có dữ liệu sau lần đầu.

## Kiểm tra tự động

```bash
cd backend && mvn -q test
cd frontend && npm run lint && npm run build
```
