import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@api/hooks/auth';

export default function Register() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    try {
      await register.mutateAsync({
        username: formData.username,
        email: formData.email,
        password: formData.password
      });
      alert('Registration successful! Please log in.');
      navigate('/login');
    } catch (err) {
      alert('Registration failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white shadow p-6 rounded border border-gray-200"
      >
        <h1 className="text-xl font-semibold mb-4">Create Account</h1>

        <label className="block mb-3">
          <span className="text-sm text-gray-700">Username</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            name="username"
            value={formData.username}
            onChange={handleChange}
            autoComplete="username"
            required
          />
        </label>

        <label className="block mb-3">
          <span className="text-sm text-gray-700">Email</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            autoComplete="email"
            required
          />
        </label>

        <label className="block mb-3">
          <span className="text-sm text-gray-700">Password</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </label>

        <label className="block mb-4">
          <span className="text-sm text-gray-700">Confirm Password</span>
          <input
            className="mt-1 w-full border rounded px-3 py-2"
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            autoComplete="new-password"
            required
          />
        </label>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          disabled={register.isPending}
        >
          {register.isPending ? 'Creating account…' : 'Create Account'}
        </button>

        <p className="text-center text-sm text-gray-600 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}