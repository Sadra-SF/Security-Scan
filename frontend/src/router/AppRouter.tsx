import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '@components/../layout/AppLayout';
import Login from '@pages/Auth/Login';
import Dashboard from '@pages/Dashboard';
import TargetsList from '@pages/Targets/List';
import TargetDetail from '@pages/Targets/Detail';
import NewScan from '@pages/Scans/NewScan';
import ScansList from '@pages/Scans/List';
import ScanDetail from '@pages/Scans/Detail';
import FindingsList from '@pages/Findings/List';
import Reports from '@pages/Reports';
import { RequireAuth } from './requireAuth';
import {
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
        <Route path="scans" element={<ScansList />} />
        <Route path="scans/new" element={<NewScan />} />
        <Route path="scans/:id" element={<ScanDetail />} />
        <Route path="findings" element={<FindingsList />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings/integrations" element={<SettingsIntegrations />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}