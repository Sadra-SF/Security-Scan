import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@api/hooks/auth';

export default function PasswordReset() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const { passwordReset } = useAuth();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await passwordReset.mutateAsync({ email });
      setSubmitted(true);
    } catch (err) {
      alert('Password reset request failed. Please try again.');
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen grid place-items-center bg-gray-50">
        <div className="w-full max-w-sm bg-white shadow p-6 rounded border border-gray-200 text-center">
          <h1 className="text-xl font-semibold mb-4">Check Your Email</h1>
          <p className="text-gray-600 mb-4">
            We've sent password reset instructions to {email}
          </p>
          <Link
            to="/login"
            className="text-blue-600 hover:underline"
          >
            Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white shadow p-6 rounded border border-gray-200"
      >
        <h1 className="text-xl font-semibold mb-4">Reset Password</h1>
        <p className="text-gray-600 text-sm mb-4">
          Enter your email address and we'll send you a link to reset your password.
        </p>

        <label className="block mb-4">
          <span className="text-sm text-gray-700">Email</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          disabled={passwordReset.isPending}
        >
          {passwordReset.isPending ? 'Sending…' : 'Send Reset Link'}
        </button>

        <p className="text-center text-sm text-gray-600 mt-4">
          Remember your password?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}