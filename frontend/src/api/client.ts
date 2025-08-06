import axios from 'axios';
import { API_BASE_URL } from '@utils/../env';
import { getAuthState, setAuthTokens, clearAuth } from '@state/auth';

// Axios instance
export const api = axios.create({
  baseURL: API_BASE_URL.replace(/\/$/, ''),
  withCredentials: false
});

// Attach JWT from localStorage/state
api.interceptors.request.use((config) => {
  const { accessToken } = getAuthState();
  if (accessToken) {
    // eslint-disable-next-line no-param-reassign
    config.headers = { ...(config.headers || {}), Authorization: `Bearer ${accessToken}` };
  }
  return config;
});

// Handle 401 with refresh flow
let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  pendingQueue.forEach((p) => {
    if (error) p.reject(error);
    else p.resolve(token);
  });
  pendingQueue = [];
};

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const status = error?.response?.status;

    if (status === 401 && !original._retry) {
      original._retry = true;
      if (isRefreshing) {
        // Queue up while refresh is in-flight
        return new Promise((resolve, reject) => {
          pendingQueue.push({
            resolve: (token) => {
              if (token) {
                original.headers.Authorization = `Bearer ${token as string}`;
              }
              resolve(api(original));
            },
            reject
          });
        });
      }

      isRefreshing = true;
      try {
        const { refreshToken } = getAuthState();
        if (!refreshToken) throw new Error('No refresh token');

        const resp = await axios.post(
          `${API_BASE_URL.replace(/\/$/, '')}/api/auth/jwt/refresh/`,
          { refresh: refreshToken }
        );

        const newAccess = resp.data?.access as string | undefined;
        if (!newAccess) throw new Error('No access token in refresh response');

        setAuthTokens({ accessToken: newAccess, refreshToken });
        processQueue(null, newAccess);
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      } catch (e) {
        processQueue(e, null);
        clearAuth();
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);