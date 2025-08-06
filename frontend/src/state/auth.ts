import { create } from 'zustand';

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: { username: string } | null;
  setTokens: (t: { accessToken: string | null; refreshToken: string | null }) => void;
  setUser: (u: { username: string } | null) => void;
  clear: () => void;
};

const STORAGE_KEY = 'ss_auth_v1';

const load = (): Pick<AuthState, 'accessToken' | 'refreshToken' | 'user'> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { accessToken: null, refreshToken: null, user: null };
    return JSON.parse(raw);
  } catch {
    return { accessToken: null, refreshToken: null, user: null };
  }
};

const persist = (data: Pick<AuthState, 'accessToken' | 'refreshToken' | 'user'>) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
};

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: load().accessToken,
  refreshToken: load().refreshToken,
  user: load().user,
  setTokens: ({ accessToken, refreshToken }) => {
    set({ accessToken, refreshToken });
    persist({ accessToken, refreshToken, user: get().user });
  },
  setUser: (user) => {
    set({ user });
    persist({ accessToken: get().accessToken, refreshToken: get().refreshToken, user });
  },
  clear: () => {
    set({ accessToken: null, refreshToken: null, user: null });
    persist({ accessToken: null, refreshToken: null, user: null });
  }
}));

// lightweight helpers for non-react modules (e.g., axios interceptors)
export const getAuthState = () => {
  const { accessToken, refreshToken, user } = useAuthStore.getState();
  return { accessToken, refreshToken, user };
};
export const setAuthTokens = (t: { accessToken: string; refreshToken: string }) =>
  useAuthStore.getState().setTokens(t);
export const setAuthUser = (u: { username: string } | null) => useAuthStore.getState().setUser(u);
export const clearAuth = () => useAuthStore.getState().clear();