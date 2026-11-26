import { Navigate, Route, Routes } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ChooseRolePage } from "./pages/ChooseRolePage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { AccountSettingsPage } from "./pages/AccountSettingsPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { accountPath } from "./utils/account";
import { PublicHomePage } from "./pages/PublicHomePage";
import { CandidateHomePage } from "./pages/candidate/CandidateHomePage";
import { CandidateCvPage } from "./pages/candidate/CandidateCvPage";
import { CandidateMatchingPage } from "./pages/candidate/CandidateMatchingPage";
import { CandidateJobDetailPage } from "./pages/candidate/CandidateJobDetailPage";
import { CandidateInterviewPage } from "./pages/candidate/CandidateInterviewPage";
import { RecruiterHomePage } from "./pages/recruiter/RecruiterHomePage";
import { RecruiterJobsPage } from "./pages/recruiter/RecruiterJobsPage";
import { RecruiterCandidatesPage } from "./pages/recruiter/RecruiterCandidatesPage";
import { RecruiterMatchingPage } from "./pages/recruiter/RecruiterMatchingPage";
import { RecruiterInterviewsPage } from "./pages/recruiter/RecruiterInterviewsPage";
import type { PermissionRequirement } from "./utils/permissions";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";
import { AdminRolesPage } from "./pages/admin/AdminRolesPage";

/** Chặn route theo quyền (specs/004-rbac); perm dạng mảng = có một trong số đó là đủ. */
function RequireAuth({
  perm,
  children,
}: {
  perm?: PermissionRequirement;
  children: React.ReactNode;
}) {
  const { user, loading, can } = useAuth();
  if (loading) return <main className="wrap page-hl muted">Đang tải…</main>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.roleChosen === false) return <Navigate to="/choose-role" replace />;
  if (perm && !can(perm)) {
    const home = accountPath(user);
    return home === location.pathname ? <main className="wrap page-hl muted">Bạn không có quyền truy cập trang này.</main>
      : <Navigate to={home} replace />;
  }
  return children;
}

function HomeGate() {
  const { user, loading } = useAuth();
  if (loading) return <main className="page">Đang tải…</main>;
  if (user) return <Navigate to={accountPath(user)} replace />;
  return <PublicHomePage />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeGate />} />
      <Route path="/jobs" element={<PublicHomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/choose-role" element={<ChooseRolePage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route
        path="/candidate"
        element={
          <RequireAuth perm={"application:read-own"}>
            <CandidateHomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/cv"
        element={
          <RequireAuth perm={"cv:manage-own"}>
            <CandidateCvPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/matching"
        element={
          <RequireAuth perm={"matching:read-own"}>
            <CandidateMatchingPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/jobs/:jobId"
        element={
          <RequireAuth perm={["application:apply", "matching:read-own"]}>
            <CandidateJobDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/profile"
        element={
          <RequireAuth>
            <AccountSettingsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/interview"
        element={
          <RequireAuth perm={"interview:practice"}>
            <CandidateInterviewPage />
          </RequireAuth>
        }
      />

      <Route
        path="/recruiter"
        element={
          <RequireAuth perm={"dashboard:recruiter"}>
            <RecruiterHomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/jobs"
        element={
          <RequireAuth perm={"job:read-own"}>
            <RecruiterJobsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/candidates"
        element={
          <RequireAuth perm={"application:read-received"}>
            <RecruiterCandidatesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/matching"
        element={
          <RequireAuth perm={["matching:run", "matching:read-all"]}>
            <RecruiterMatchingPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/interviews"
        element={
          <RequireAuth perm={"question:read"}>
            <RecruiterInterviewsPage />
          </RequireAuth>
        }
      />

      <Route
        path="/admin/users"
        element={
          <RequireAuth perm="user:read">
            <AdminUsersPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/roles"
        element={
          <RequireAuth perm="role:manage">
            <AdminRolesPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
