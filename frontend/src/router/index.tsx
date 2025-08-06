import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Login from '@pages/Auth/Login';
// Temporary placeholders until pages are implemented and deps installed
import {
  Dashboard,
  TargetsList,
  TargetDetail,
  NewScan,
  ScanDetail,
  Findings,
  Reports,
  SettingsIntegrations
} from './_tempPlaceholders';
import { RequireAuth } from './requireAuth';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Navigate to="/dashboard" replace />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/targets"
        element={
          <RequireAuth>
            <TargetsList />
          </RequireAuth>
        }
      />
      <Route
        path="/targets/:id"
        element={
          <RequireAuth>
            <TargetDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/scans/new"
        element={
          <RequireAuth>
            <NewScan />
          </RequireAuth>
        }
      />
      <Route
        path="/scans/:id"
        element={
          <RequireAuth>
            <ScanDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/findings"
        element={
          <RequireAuth>
            <Findings />
          </RequireAuth>
        }
      />
      <Route
        path="/reports"
        element={
          <RequireAuth>
            <Reports />
          </RequireAuth>
        }
      />
      <Route
        path="/settings/integrations"
        element={
          <RequireAuth>
            <SettingsIntegrations />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}