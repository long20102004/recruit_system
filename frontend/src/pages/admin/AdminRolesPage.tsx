import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { adminApi, ApiError, type RbacMatrixDto } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

/** Quyền không được gỡ khỏi ADMIN (backend cũng chặn). */
const LOCKED = { role: "ADMIN", perm: "role:manage" };

/** Ma trận phân quyền Role × Permission (quyền role:manage). Lưu theo từng role. */
export function AdminRolesPage() {
  const { toast } = useToast();
  const { user, refreshUser } = useAuth();
  const [matrix, setMatrix] = useState<RbacMatrixDto | null>(null);
  const [draft, setDraft] = useState<Record<string, Set<string>>>({});
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(() => {
    adminApi.roles()
      .then((m) => {
        setMatrix(m);
        setDraft(Object.fromEntries(m.roles.map((r) => [r.code, new Set(r.permissions)])));
      })
      .catch((e) => toast(e instanceof ApiError ? e.message : "Không tải được ma trận phân quyền"));
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const groups = useMemo(() => {
    const out = new Map<string, RbacMatrixDto["permissions"]>();
    for (const p of matrix?.permissions ?? []) out.set(p.resource, [...(out.get(p.resource) ?? []), p]);
    return [...out.entries()];
  }, [matrix]);

  const dirty = (code: string) => {
    const saved = new Set(matrix?.roles.find((r) => r.code === code)?.permissions ?? []);
    const cur = draft[code] ?? new Set();
    return saved.size !== cur.size || [...cur].some((p) => !saved.has(p));
  };

  function toggle(role: string, perm: string) {
    setDraft((d) => {
      const next = new Set(d[role]);
      if (next.has(perm)) next.delete(perm); else next.add(perm);
      return { ...d, [role]: next };
    });
  }

  async function save(code: string) {
    setSaving(code);
    try {
      await adminApi.updateRole(code, [...(draft[code] ?? [])]);
      if (code === user?.role) await refreshUser();
      toast(`Đã lưu quyền của ${code}. Áp dụng ngay cho mọi phiên đăng nhập.`);
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không lưu được");
    } finally {
      setSaving(null);
    }
  }

  return (
    <RecruiterLayout active="roles">
      <div className="page-head">
        <div>
          <p className="kicker">Quản trị · RBAC</p>
          <h1 style={{ fontSize: 32, marginTop: 4 }}>Phân quyền</h1>
          <p className="muted">Mỗi người dùng có một vai trò; vai trò quyết định các quyền bên dưới. Lưu xong có hiệu lực ngay.</p>
        </div>
      </div>
      {!matrix ? (
        <EmptyNote>Đang tải…</EmptyNote>
      ) : (
        <div className="tbl-box">
          <table className="tbl">
            <thead>
              <tr>
                <th>Quyền</th>
                {matrix.roles.map((r) => (
                  <th key={r.code} style={{ textAlign: "center", width: 150 }}>{r.name}<br /><span className="tiny">{r.code}</span></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map(([resource, perms]) => (
                <Fragment key={resource}>
                  <tr>
                    <td colSpan={matrix.roles.length + 1} className="tiny"
                      style={{ background: "var(--surface)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--muted)" }}>
                      {resource}
                    </td>
                  </tr>
                  {perms.map((p) => (
                    <tr key={p.code}>
                      <td>
                        <p style={{ fontWeight: 600, fontSize: 14 }}>{p.description}</p>
                        <code className="tiny muted">{p.code}</code>
                      </td>
                      {matrix.roles.map((r) => {
                        const locked = r.code === LOCKED.role && p.code === LOCKED.perm;
                        return (
                          <td key={r.code} style={{ textAlign: "center" }}>
                            <input type="checkbox" aria-label={`${r.code} ${p.code}`} disabled={locked}
                              title={locked ? "Không thể gỡ quyền này khỏi ADMIN" : undefined}
                              checked={draft[r.code]?.has(p.code) ?? false} onChange={() => toggle(r.code, p.code)}
                              style={{ width: 18, height: 18, accentColor: "var(--brand)" }} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </Fragment>
              ))}
              <tr>
                <td className="small muted">Lưu thay đổi theo vai trò</td>
                {matrix.roles.map((r) => (
                  <td key={r.code} style={{ textAlign: "center" }}>
                    <button type="button" className={dirty(r.code) ? "btn btn-p btn-sm" : "btn btn-g btn-sm"}
                      disabled={!dirty(r.code) || saving !== null} onClick={() => save(r.code)}>
                      {saving === r.code ? "Đang lưu…" : "Lưu"}
                    </button>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </RecruiterLayout>
  );
}
