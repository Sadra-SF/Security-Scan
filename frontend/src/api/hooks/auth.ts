import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@api/client';
import { setAuthTokens, setAuthUser, clearAuth } from '@state/auth';

const LoginResponse = z.object({
  access: z.string(),
  refresh: z.string()
});

type LoginInput = { username: string; password: string };

export function useAuth() {
  const login = useMutation({
    mutationKey: ['auth', 'login'],
    mutationFn: async ({ username, password }: LoginInput) => {
      const { data } = await api.post('/api/auth/jwt/create/', { username, password });
      const parsed = LoginResponse.parse(data);
      setAuthTokens({ accessToken: parsed.access, refreshToken: parsed.refresh });
      setAuthUser({ username });
      return parsed;
    }
  });

  const logout = () => {
    clearAuth();
  };

  return { login, logout };
}