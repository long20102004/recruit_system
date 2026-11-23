import { Navigate, Route, Routes } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ChooseRolePage } from "./pages/ChooseRolePage";
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
import type { RoleDto } from "./api/client";

function RequireAuth({
  roles,
  children,
}: {
  roles?: RoleDto[];
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  if (loading) return <main className="page">Đang tải…</main>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.roleChosen === false) return <Navigate to="/choose-role" replace />;
  if (roles && !roles.includes(user.role) && user.role !== "ADMIN") {
    return <Navigate to={accountPath(user)} replace />;
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

      <Route
        path="/candidate"
        element={
          <RequireAuth roles={["CANDIDATE"]}>
            <CandidateHomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/cv"
        element={
          <RequireAuth roles={["CANDIDATE"]}>
            <CandidateCvPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/matching"
        element={
          <RequireAuth roles={["CANDIDATE"]}>
            <CandidateMatchingPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/jobs/:jobId"
        element={
          <RequireAuth roles={["CANDIDATE"]}>
            <CandidateJobDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/candidate/interview"
        element={
          <RequireAuth roles={["CANDIDATE"]}>
            <CandidateInterviewPage />
          </RequireAuth>
        }
      />

      <Route
        path="/recruiter"
        element={
          <RequireAuth roles={["RECRUITER"]}>
            <RecruiterHomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/jobs"
        element={
          <RequireAuth roles={["RECRUITER"]}>
            <RecruiterJobsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/candidates"
        element={
          <RequireAuth roles={["RECRUITER"]}>
            <RecruiterCandidatesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/matching"
        element={
          <RequireAuth roles={["RECRUITER"]}>
            <RecruiterMatchingPage />
          </RequireAuth>
        }
      />
      <Route
        path="/recruiter/interviews"
        element={
          <RequireAuth roles={["RECRUITER"]}>
            <RecruiterInterviewsPage />
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
