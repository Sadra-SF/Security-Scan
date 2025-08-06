import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '@components/../layout/AppLayout';
import Login from '@pages/Auth/Login';
import { RequireAuth } from './requireAuth';
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

/**
 * Central router with layout; guarded routes render inside AppLayout.
 * Replace temp placeholders with real page components as they are implemented.
 */
export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="targets" element={<TargetsList />} />
        <Route path="targets/:id" element={<TargetDetail />} />
        <Route path="scans/new" element={<NewScan />} />
        <Route path="scans/:id" element={<ScanDetail />} />
        <Route path="findings" element={<Findings />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings/integrations" element={<SettingsIntegrations />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}