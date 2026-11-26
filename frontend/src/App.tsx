import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ChooseRolePage } from "./pages/ChooseRolePage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { AccountSettingsPage } from "./pages/AccountSettingsPage";
import { CandidateApplicationsPage } from "./pages/candidate/CandidateApplicationsPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { accountPath, loginPath } from "./utils/account";
import { PublicHomePage } from "./pages/PublicHomePage";
import { LandingPage } from "./pages/LandingPage";
import { CandidateHomePage } from "./pages/candidate/CandidateHomePage";
import { CandidateCvPage } from "./pages/candidate/CandidateCvPage";
import { CandidateMatchingPage } from "./pages/candidate/CandidateMatchingPage";
import { CandidateJobDetailPage } from "./pages/candidate/CandidateJobDetailPage";
import { CandidateInterviewPage } from "./pages/candidate/CandidateInterviewPage";
import { RecruiterHomePage } from "./pages/recruiter/RecruiterHomePage";
import { RecruiterJobsPage } from "./pages/recruiter/RecruiterJobsPage";
import { RecruiterJobEditorPage } from "./pages/recruiter/RecruiterJobEditorPage";
import { RecruiterCandidatesPage } from "./pages/recruiter/RecruiterCandidatesPage";
import { RecruiterMatchingPage } from "./pages/recruiter/RecruiterMatchingPage";
import { RecruiterInterviewsPage } from "./pages/recruiter/RecruiterInterviewsPage";
import type { PermissionRequirement } from "./utils/permissions";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";
import { AdminRolesPage } from "./pages/admin/AdminRolesPage";
// Màn dùng dữ liệu mẫu (src/api/mock), chờ nối API.
import { CandidateCvListPage } from "./pages/candidate/CandidateCvListPage";
import { CandidateSavedJobsPage } from "./pages/candidate/CandidateSavedJobsPage";
import { CandidateJobAlertsPage } from "./pages/candidate/CandidateJobAlertsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { CompanyListPage } from "./pages/CompanyListPage";
import { CompanyDetailPage } from "./pages/CompanyDetailPage";
import { CompanyRegisterPage } from "./pages/recruiter/CompanyRegisterPage";
import { RecruiterCompanyPage } from "./pages/recruiter/RecruiterCompanyPage";
import { RecruiterTeamPage } from "./pages/recruiter/RecruiterTeamPage";
import { RecruiterCvSearchPage } from "./pages/recruiter/RecruiterCvSearchPage";
import { RecruiterInterviewResultsPage } from "./pages/recruiter/RecruiterInterviewResultsPage";
import { RecruiterApplicationDetailPage } from "./pages/recruiter/RecruiterApplicationDetailPage";
import { AdminDashboardPage } from "./pages/admin/AdminDashboardPage";
import { AdminCompaniesPage } from "./pages/admin/AdminCompaniesPage";
import { AdminJobsPage } from "./pages/admin/AdminJobsPage";
import { AdminCvTemplatesPage } from "./pages/admin/AdminCvTemplatesPage";
import { AdminQuestionBankPage } from "./pages/admin/AdminQuestionBankPage";

/** Chặn route theo quyền (specs/004-rbac); perm dạng mảng = có một trong số đó là đủ. */
function RequireAuth({
  perm,
  children,
}: {
  perm?: PermissionRequirement;
  children: React.ReactNode;
}) {
  const { user, loading, can, loggedOut } = useAuth();
  const location = useLocation();
  if (loading) return <main className="wrap page-hl muted">Đang tải…</main>;
  // Vừa bấm đăng xuất: về trang chủ, không mở trang đăng nhập kèm ?redirect.
  if (!user) return <Navigate to={loggedOut ? "/" : loginPath(location.pathname + location.search)} replace />;
  if (user.roleChosen === false) return <Navigate to="/choose-role" replace />;
  if (perm && !can(perm)) {
    const home = accountPath(user);
    return home === location.pathname ? <main className="wrap page-hl muted">Bạn không có quyền truy cập trang này.</main>
      : <Navigate to={home} replace />;
  }
  return children;
}

/** Ứng viên dùng trang Tổng quan (đã gộp danh sách việc làm); khách và recruiter giữ trang /jobs. */
function JobsGate() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <main className="page">Đang tải…</main>;
  if (user?.role === "CANDIDATE") return <Navigate to={`/candidate${location.search}`} replace />;
  return <PublicHomePage />;
}

function HomeGate() {
  const { user, loading } = useAuth();
  if (loading) return <main className="page">Đang tải…</main>;
  if (user) return <Navigate to={accountPath(user)} replace />;
  return <LandingPage />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeGate />} />
      <Route path="/jobs" element={<JobsGate />} />
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
        path="/candidate/applications"
        element={
          <RequireAuth perm={"application:read-own"}>
            <CandidateApplicationsPage />
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
        path="/recruiter/jobs/new"
        element={
          <RequireAuth perm={"job:create"}>
            <RecruiterJobEditorPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/jobs/:id/edit"
        element={
          <RequireAuth perm={"job:update"}>
            <RecruiterJobEditorPage />
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
      {/* Màn dùng dữ liệu mẫu */}
      <Route path="/companies" element={<CompanyListPage />} />
      <Route path="/companies/:id" element={<CompanyDetailPage />} />
      <Route
        path="/notifications"
        element={
          <RequireAuth>
            <NotificationsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/cvs"
        element={
          <RequireAuth perm={"cv:manage-own"}>
            <CandidateCvListPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/saved"
        element={
          <RequireAuth perm={"application:read-own"}>
            <CandidateSavedJobsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/alerts"
        element={
          <RequireAuth perm={"application:read-own"}>
            <CandidateJobAlertsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/company/register"
        element={
          <RequireAuth perm={"job:read-own"}>
            <CompanyRegisterPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/company"
        element={
          <RequireAuth perm={"job:read-own"}>
            <RecruiterCompanyPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/team"
        element={
          <RequireAuth perm={"job:read-own"}>
            <RecruiterTeamPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/cv-search"
        element={
          <RequireAuth perm={"job:read-own"}>
            <RecruiterCvSearchPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/interview-results"
        element={
          <RequireAuth perm={"job:read-own"}>
            <RecruiterInterviewResultsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/candidates/:id"
        element={
          <RequireAuth perm={"application:read-received"}>
            <RecruiterApplicationDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth perm={"user:read"}>
            <AdminDashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/companies"
        element={
          <RequireAuth perm={"user:read"}>
            <AdminCompaniesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/jobs"
        element={
          <RequireAuth perm={"user:read"}>
            <AdminJobsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/cv-templates"
        element={
          <RequireAuth perm={"user:read"}>
            <AdminCvTemplatesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/questions"
        element={
          <RequireAuth perm={"user:read"}>
            <AdminQuestionBankPage />
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
