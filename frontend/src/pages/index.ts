// Temporary re-exports mapping to actual page files when created.
// For now, keep zero-JSX fallbacks to avoid TS parse errors without React installed.

export const Dashboard = () => 'Dashboard (to be implemented)' as unknown as JSX.Element;
export const TargetsList = () => 'Targets List (to be implemented)' as unknown as JSX.Element;
export const TargetDetail = () => 'Target Detail (to be implemented)' as unknown as JSX.Element;
export const NewScan = () => 'New Scan (to be implemented)' as unknown as JSX.Element;
export const ScanDetail = () => 'Scan Detail (to be implemented)' as unknown as JSX.Element;
export const Findings = () => 'Findings (to be implemented)' as unknown as JSX.Element;
export const Reports = () => 'Reports (to be implemented)' as unknown as JSX.Element;
export const SettingsIntegrations = () =>
  'Settings & Integrations (to be implemented)' as unknown as JSX.Element;