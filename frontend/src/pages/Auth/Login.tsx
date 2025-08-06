import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@api/hooks/auth';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const nav = useNavigate();
  const location = useLocation() as any;

  const from = location.state?.from?.pathname || '/dashboard';

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login.mutateAsync({ username, password });
      nav(from, { replace: true });
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert('Login failed. Check credentials.');
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white shadow p-6 rounded border border-gray-200"
      >
        <h1 className="text-xl font-semibold mb-4">Sign in</h1>
        <label className="block mb-3">
          <span className="text-sm text-gray-700">Username</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="block mb-4">
          <span className="text-sm text-gray-700">Password</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          disabled={login.isPending}
        >
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="text-xs text-gray-500 mt-3">
          Endpoint: /api/auth/jwt/create (configurable in backend).
        </p>
      </form>
    </div>
  );
}