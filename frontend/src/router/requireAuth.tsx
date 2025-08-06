import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@state/auth';

type Props = { children: React.ReactNode };

export function RequireAuth({ children }: Props) {
  const access = useAuthStore((s) => s.accessToken);
  const location = useLocation();

  if (!access) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}