import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  authApi,
  getToken,
  setToken,
  type RegisterResponse,
  type RoleDto,
  type UserDto,
} from "../api/client";
import { hasPermission, type PermissionRequirement } from "../utils/permissions";
import type { HeaderMode, UserRole } from "../types";

interface AuthState {
  user: UserDto | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserDto>;
  /** Đăng nhập bằng Google: credential là ID token Google trả về cho nút Google. */
  loginWithGoogle: (credential: string) => Promise<UserDto>;
  /** Tạo tài khoản; chưa đăng nhập cho tới khi xác thực email. */
  register: (input: { email: string; password: string }) => Promise<RegisterResponse>;
  /** Dùng token trong link xác thực email; thành công thì đăng nhập luôn. */
  verifyEmail: (token: string) => Promise<UserDto>;
  chooseRole: (role: "CANDIDATE" | "RECRUITER") => Promise<UserDto>;
  refreshUser: () => Promise<void>;
  logout: () => void;
  /** Kiểm tra quyền theo ma trận RBAC; mảng = có một trong số đó là đủ. */
  can: (need: PermissionRequirement) => boolean;
  headerMode: HeaderMode;
  uiRole: UserRole | null;
}

const AuthContext = createContext<AuthState | null>(null);

function roleToHeader(role: RoleDto | undefined): HeaderMode {
  if (role === "RECRUITER" || role === "ADMIN") return "recruiter";
  if (role === "CANDIDATE") return "candidate";
  return "public";
}

function roleToUi(role: RoleDto | undefined): UserRole | null {
  if (role === "RECRUITER" || role === "ADMIN") return "recruiter";
  if (role === "CANDIDATE") return "candidate";
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserDto | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const loginWithGoogle = useCallback(async (credential: string) => {
    const res = await authApi.google(credential);
    setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const register = useCallback(
    (input: { email: string; password: string }) => authApi.register(input),
    []
  );

  const verifyEmail = useCallback(async (token: string) => {
    const res = await authApi.verifyEmail(token);
    setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const chooseRole = useCallback(async (role: "CANDIDATE" | "RECRUITER") => {
    const res = await authApi.chooseRole(role);
    setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const refreshUser = useCallback(async () => {
    if (!getToken()) return;
    const me = await authApi.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      login,
      loginWithGoogle,
      register,
      verifyEmail,
      chooseRole,
      refreshUser,
      logout,
      can: (need: PermissionRequirement) => hasPermission(user, need),
      headerMode: roleToHeader(user?.role),
      uiRole: roleToUi(user?.role),
    }),
    [user, loading, login, loginWithGoogle, register, verifyEmail, chooseRole, refreshUser, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
