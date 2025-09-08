import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@api/client';
import { setAuthTokens, setAuthUser, clearAuth } from '@state/auth';

const LoginResponse = z.object({
  access: z.string(),
  refresh: z.string()
});

const RegisterResponse = z.object({
  username: z.string(),
  email: z.string()
});

const PasswordResetResponse = z.object({
  detail: z.string()
});

type LoginInput = { username: string; password: string };
type RegisterInput = { username: string; email: string; password: string };
type PasswordResetInput = { email: string };

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

  const register = useMutation({
    mutationKey: ['auth', 'register'],
    mutationFn: async ({ username, email, password }: RegisterInput) => {
      const { data } = await api.post('/api/auth/users/', { username, email, password });
      const parsed = RegisterResponse.parse(data);
      return parsed;
    }
  });

  const passwordReset = useMutation({
    mutationKey: ['auth', 'password-reset'],
    mutationFn: async ({ email }: PasswordResetInput) => {
      const { data } = await api.post('/api/auth/users/reset_password/', { email });
      const parsed = PasswordResetResponse.parse(data);
      return parsed;
    }
  });

  const logout = () => {
    clearAuth();
  };

  return { login, register, passwordReset, logout };
}