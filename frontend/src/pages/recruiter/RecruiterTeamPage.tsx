import { useEffect, useState, type FormEvent } from "react";
import { EmptyNote, MockNote, RecruiterLayout, Table } from "../../components/common";
import {
  getTeamData,
  inviteTeamMember,
  removeTeamMember,
  resendTeamInvite,
  revokeTeamInvite,
  updateMemberRole,
  type EditableCompanyRole,
  type TeamInvite,
  type TeamMember,
} from "../../api/mock/recruiterMock";
import { useToast } from "../../context/ToastContext";
import { initials } from "../../utils/format";

const EDITABLE_ROLES: readonly EditableCompanyRole[] = ["Manager", "Recruiter", "Viewer"];

export function RecruiterTeamPage() {
  const { toast } = useToast();
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [invites, setInvites] = useState<TeamInvite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("minh.tran@gmail.com");
  const [inviteRole, setInviteRole] = useState<EditableCompanyRole>("Recruiter");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getTeamData()
      .then((data) => {
        setMembers(data.members);
        setInvites(data.invites);
      })
      .catch((e) => {
        setMembers([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách thành viên");
      });
  }, [toast]);

  async function handleRoleChange(memberId: number, role: EditableCompanyRole) {
    try {
      const updated = await updateMemberRole(memberId, role);
      setMembers((prev) => (prev ?? []).map((m) => (m.id === memberId ? updated : m)));
      toast(`Đã đổi vai trò của ${updated.name} thành ${updated.role}.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không đổi được vai trò");
    }
  }

  async function handleRemoveMember(member: TeamMember) {
    try {
      await removeTeamMember(member.id);
      setMembers((prev) => (prev ?? []).filter((m) => m.id !== member.id));
      toast(`Đã xoá ${member.name} khỏi công ty.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không xoá được thành viên");
    }
  }

  async function handleResendInvite(inv: TeamInvite) {
    try {
      const updated = await resendTeamInvite(inv.id);
      setInvites((prev) => prev.map((x) => (x.id === inv.id ? updated : x)));
      toast(`Đã gửi lại lời mời tới ${inv.email}.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Gửi lại lời mời thất bại");
    }
  }

  async function handleRevokeInvite(inv: TeamInvite) {
    try {
      await revokeTeamInvite(inv.id);
      setInvites((prev) => prev.filter((x) => x.id !== inv.id));
      toast(`Đã thu hồi lời mời của ${inv.email}.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Thu hồi lời mời thất bại");
    }
  }

  async function handleInviteSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setInviteError(null);
    setBusy(true);
    try {
      const created = await inviteTeamMember(inviteEmail, inviteRole);
      setInvites((prev) => [created, ...prev]);
      setInviteEmail("");
      toast(`Đã gửi lời mời tới ${created.email}.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Gửi lời mời thất bại";
      setInviteError(msg);
      toast(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="team">
      <MockNote />

      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Thành viên</h1>
          <p className="muted">
            {members === null
              ? "Đang tải…"
              : `${members.length} thành viên · ${invites.length} lời mời đang chờ`}
          </p>
        </div>
      </div>

      {members === null ? (
        <p className="muted">Đang tải danh sách thành viên…</p>
      ) : (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 18 }}>
            <Table>
              <thead>
                <tr>
                  <th>Thành viên</th>
                  <th>Vai trò</th>
                  <th>Tham gia</th>
                  <th style={{ textAlign: "right" }}>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                        <span className="avatar">{initials(m.name)}</span>
                        <div>
                          <p style={{ fontWeight: 650 }}>{m.name}</p>
                          <p className="tiny muted">{m.email}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      {m.role === "Owner" ? (
                        <span className="badge b-brand b-plain">Owner</span>
                      ) : (
                        <select
                          className="input"
                          aria-label={`Vai trò của ${m.name}`}
                          style={{ height: 36, width: "auto" }}
                          value={m.role}
                          onChange={(e) =>
                            void handleRoleChange(m.id, e.target.value as EditableCompanyRole)
                          }
                        >
                          {EDITABLE_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="small muted">{m.joinedAt}</td>
                    <td style={{ textAlign: "right" }}>
                      {m.role !== "Owner" ? (
                        <button
                          type="button"
                          className="btn btn-d btn-sm"
                          onClick={() => void handleRemoveMember(m)}
                        >
                          Xoá khỏi công ty
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>

            <section className="stack" style={{ gap: 10 }}>
              <h2 style={{ fontSize: 20 }}>Lời mời đang chờ</h2>
              {invites.length === 0 ? (
                <EmptyNote>Không có lời mời nào đang chờ.</EmptyNote>
              ) : (
                <Table style={{ minWidth: 640 }}>
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Vai trò</th>
                      <th>Mời bởi</th>
                      <th>Hết hạn</th>
                      <th style={{ textAlign: "right" }} aria-label="Thao tác" />
                    </tr>
                  </thead>
                  <tbody>
                    {invites.map((inv) => (
                      <tr key={inv.id}>
                        <td>{inv.email}</td>
                        <td>{inv.role}</td>
                        <td className="small">{inv.invitedBy}</td>
                        <td className="small">{inv.expiresAt}</td>
                        <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                          <button
                            type="button"
                            className="btn btn-g btn-sm"
                            onClick={() => void handleResendInvite(inv)}
                          >
                            Gửi lại
                          </button>{" "}
                          <button
                            type="button"
                            className="btn btn-d btn-sm"
                            onClick={() => void handleRevokeInvite(inv)}
                          >
                            Thu hồi
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </section>
          </div>

          <aside style={{ flex: "1 1 320px", maxWidth: 380, display: "flex", flexDirection: "column", gap: 16 }}>
            <form className="card stack" style={{ gap: 14 }} noValidate onSubmit={(e) => void handleInviteSubmit(e)}>
              <h3 style={{ fontSize: 18 }}>Mời thành viên</h3>
              <div className="field">
                <label htmlFor="invite-email">Email</label>
                <input
                  id="invite-email"
                  className="input"
                  type="email"
                  placeholder="ten@congty.vn"
                  value={inviteEmail}
                  onChange={(e) => {
                    setInviteEmail(e.target.value);
                    if (inviteError) setInviteError(null);
                  }}
                />
                <span className="help">Người được mời phải có tài khoản HireLens.</span>
              </div>
              <div className="field">
                <label htmlFor="invite-role">Vai trò</label>
                <select
                  id="invite-role"
                  className="input"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as EditableCompanyRole)}
                >
                  {EDITABLE_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-p" disabled={busy}>
                {busy ? "Đang gửi…" : "Gửi lời mời"}
              </button>
              {inviteError ? (
                <div className="note note-warn small" role="alert">
                  {inviteError}
                </div>
              ) : null}
            </form>

            <section className="card stack" style={{ gap: 8 }}>
              <h4>Quyền theo vai trò</h4>
              <dl style={{ margin: 0, display: "grid", gap: 8, fontSize: 13.5 }}>
                <div>
                  <dt style={{ fontWeight: 650 }}>Owner</dt>
                  <dd style={{ margin: 0 }} className="muted">
                    Toàn quyền, chuyển quyền sở hữu.
                  </dd>
                </div>
                <div>
                  <dt style={{ fontWeight: 650 }}>Manager</dt>
                  <dd style={{ margin: 0 }} className="muted">
                    Sửa công ty, mời thành viên, đăng tin, xử lý đơn.
                  </dd>
                </div>
                <div>
                  <dt style={{ fontWeight: 650 }}>Recruiter</dt>
                  <dd style={{ margin: 0 }} className="muted">
                    Đăng tin, xử lý đơn, mời phỏng vấn.
                  </dd>
                </div>
                <div>
                  <dt style={{ fontWeight: 650 }}>Viewer</dt>
                  <dd style={{ margin: 0 }} className="muted">
                    Chỉ xem tin và đơn.
                  </dd>
                </div>
              </dl>
            </section>
          </aside>
        </div>
      )}
    </RecruiterLayout>
  );
}
