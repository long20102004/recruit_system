import { useCallback, useEffect, useState } from "react";
import { Can, EmptyNote, Pager, RecruiterLayout } from "../../components/common";
import { adminApi, ApiError, type AdminUserDto, type PageDto } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { initials, shortDate } from "../../utils/format";

const ROLE_LABEL: Record<string, string> = { CANDIDATE: "Ứng viên", RECRUITER: "Nhà tuyển dụng", ADMIN: "Quản trị" };
const STATUS: Record<string, { label: string; cls: string }> = {
  ACTIVE: { label: "Hoạt động", cls: "badge b-ok" },
  INACTIVE: { label: "Không hoạt động", cls: "badge b-plain" },
  BANNED: { label: "Bị khoá", cls: "badge b-danger" },
};

/** Quản trị người dùng (quyền user:read; khoá / mở khoá cần user:lock). */
export function AdminUsersPage() {
  const { toast } = useToast();
  const { user: me } = useAuth();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<PageDto<AdminUserDto> | null>(null);
  const [lockingId, setLockingId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    adminApi.users({ q, status, page }).then(setData)
      .catch((e) => toast(e instanceof ApiError ? e.message : "Không tải được người dùng"));
  }, [q, status, page, toast]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  async function lock(id: number) {
    if (!reason.trim()) { toast("Nhập lý do khoá"); return; }
    setBusy(true);
    try {
      await adminApi.lock(id, reason.trim());
      toast("Đã khoá tài khoản");
      setLockingId(null); setReason(""); load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không khoá được");
    } finally { setBusy(false); }
  }

  async function unlock(id: number) {
    setBusy(true);
    try {
      await adminApi.unlock(id);
      toast("Đã mở khoá");
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không mở khoá được");
    } finally { setBusy(false); }
  }

  return (
    <RecruiterLayout active="users">
      <div className="page-head">
        <div>
          <p className="kicker">Quản trị</p>
          <h1 style={{ fontSize: 32, marginTop: 4 }}>Người dùng</h1>
          <p className="muted">Khoá tài khoản sẽ đăng xuất người đó khỏi mọi thiết bị ngay lập tức.</p>
        </div>
      </div>
      <div className="row">
        <input className="input" type="search" placeholder="Tìm theo email hoặc họ tên" aria-label="Tìm người dùng"
          style={{ flex: "1 1 260px", maxWidth: 360 }} value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} />
        <select className="input" aria-label="Trạng thái" style={{ width: "auto" }} value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(0); }}>
          <option value="">Mọi trạng thái</option>
          <option value="ACTIVE">Hoạt động</option>
          <option value="BANNED">Bị khoá</option>
          <option value="INACTIVE">Không hoạt động</option>
        </select>
        {data ? <span className="small muted">{data.totalElements} người dùng</span> : null}
      </div>
      {!data ? (
        <EmptyNote>Đang tải…</EmptyNote>
      ) : data.content.length === 0 ? (
        <EmptyNote>Không có người dùng phù hợp.</EmptyNote>
      ) : (
        <div className="tbl-box">
          <table className="tbl">
            <thead><tr><th>Người dùng</th><th>Vai trò</th><th>Trạng thái</th><th>Email</th><th>Tạo</th><th /></tr></thead>
            <tbody>
              {data.content.map((u) => {
                const st = STATUS[u.status] ?? { label: u.status, cls: "badge" };
                const self = me?.id === u.id;
                return (
                  <tr key={u.id}>
                    <td>
                      <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                        <span className="avatar">{initials(u.fullName)}</span>
                        <div style={{ minWidth: 0 }}>
                          <p style={{ fontWeight: 650 }}>{u.fullName}</p>
                          <p className="tiny muted">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="small">{ROLE_LABEL[u.role] ?? u.role}</td>
                    <td>
                      <span className={st.cls}>{st.label}</span>
                      {u.lockedReason ? <p className="tiny muted" style={{ marginTop: 4 }}>{u.lockedReason}</p> : null}
                    </td>
                    <td className="small">{u.emailVerified ? "Đã xác thực" : <span className="muted">Chưa xác thực</span>}</td>
                    <td className="small muted">{shortDate(u.createdAt)}</td>
                    <td style={{ minWidth: 220 }}>
                      <Can perm="user:lock">
                        {u.status === "BANNED" ? (
                          <button type="button" className="btn btn-g btn-sm" disabled={busy} onClick={() => unlock(u.id)}>Mở khoá</button>
                        ) : self || u.role === "ADMIN" ? null : lockingId === u.id ? (
                          <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                            <input className="input" style={{ height: 36 }} placeholder="Lý do khoá" aria-label="Lý do khoá"
                              value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
                            <button type="button" className="btn btn-d btn-sm" disabled={busy} onClick={() => lock(u.id)}>Khoá</button>
                            <button type="button" className="btn btn-sm" onClick={() => { setLockingId(null); setReason(""); }}>Huỷ</button>
                          </div>
                        ) : (
                          <button type="button" className="btn btn-d btn-sm" onClick={() => { setLockingId(u.id); setReason(""); }}>Khoá</button>
                        )}
                      </Can>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <Pager data={data} onPage={setPage} />
    </RecruiterLayout>
  );
}
