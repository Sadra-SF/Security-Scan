import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useAuthStore } from '@state/auth';

type ProfileFormData = {
  firstName: string;
  lastName: string;
  email: string;
  timezone: string;
};

type NotificationSettings = {
  emailAlerts: boolean;
  scanComplete: boolean;
  criticalFindings: boolean;
  weeklyReports: boolean;
  slackNotifications: boolean;
};

type SecuritySettings = {
  twoFactorEnabled: boolean;
  sessionTimeout: string;
  passwordExpiry: string;
};

const SETTINGS_TABS = [
  { id: 'profile', name: 'Profile', icon: '👤' },
  { id: 'security', name: 'Security', icon: '🔒' },
  { id: 'notifications', name: 'Notifications', icon: '🔔' },
  { id: 'integrations', name: 'Integrations', icon: '🔗' },
  { id: 'preferences', name: 'Preferences', icon: '⚙️' }
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState('profile');
  const user = useAuthStore((s) => s.user);

  const profileForm = useForm<ProfileFormData>({
    defaultValues: {
      firstName: '',
      lastName: '',
      email: user?.username || '',
      timezone: 'UTC'
    }
  });

  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    emailAlerts: true,
    scanComplete: true,
    criticalFindings: true,
    weeklyReports: false,
    slackNotifications: false
  });

  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    twoFactorEnabled: false,
    sessionTimeout: '30',
    passwordExpiry: '90'
  });

  const onProfileSubmit = (data: ProfileFormData) => {
    // Handle profile update
    console.log('Profile update:', data);
  };

  const updateNotificationSetting = (key: keyof NotificationSettings, value: boolean) => {
    setNotificationSettings(prev => ({ ...prev, [key]: value }));
  };

  const updateSecuritySetting = (key: keyof SecuritySettings, value: string | boolean) => {
    setSecuritySettings(prev => ({ ...prev, [key]: value }));
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">Profile Information</h2>
              <p className="text-gray-600">Update your personal information and preferences.</p>
            </div>

            <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                  <input
                    {...profileForm.register('firstName')}
                    className="w-full border rounded px-3 py-2"
                    placeholder="Enter your first name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                  <input
                    {...profileForm.register('lastName')}
                    className="w-full border rounded px-3 py-2"
                    placeholder="Enter your last name"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                <input
                  {...profileForm.register('email')}
                  type="email"
                  className="w-full border rounded px-3 py-2"
                  placeholder="Enter your email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timezone</label>
                <select {...profileForm.register('timezone')} className="w-full border rounded px-3 py-2">
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Chicago">Central Time</option>
                  <option value="America/Denver">Mountain Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Europe/Paris">Paris</option>
                  <option value="Asia/Tokyo">Tokyo</option>
                </select>
              </div>

              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save Changes
              </button>
            </form>
          </div>
        );

      case 'security':
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">Security Settings</h2>
              <p className="text-gray-600">Manage your account security and authentication preferences.</p>
            </div>

            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h3 className="font-medium">Two-Factor Authentication</h3>
                  <p className="text-sm text-gray-600">Add an extra layer of security to your account</p>
                </div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={securitySettings.twoFactorEnabled}
                    onChange={(e) => updateSecuritySetting('twoFactorEnabled', e.target.checked)}
                    className="rounded"
                  />
                  <span className="ml-2 text-sm">Enable</span>
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Session Timeout (minutes)</label>
                  <select
                    value={securitySettings.sessionTimeout}
                    onChange={(e) => updateSecuritySetting('sessionTimeout', e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="15">15 minutes</option>
                    <option value="30">30 minutes</option>
                    <option value="60">1 hour</option>
                    <option value="240">4 hours</option>
                    <option value="480">8 hours</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Password Expiry (days)</label>
                  <select
                    value={securitySettings.passwordExpiry}
                    onChange={(e) => updateSecuritySetting('passwordExpiry', e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="30">30 days</option>
                    <option value="60">60 days</option>
                    <option value="90">90 days</option>
                    <option value="180">180 days</option>
                    <option value="365">1 year</option>
                  </select>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="font-medium">Password Management</h3>
                <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Change Password
                </button>
                <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 ml-4">
                  View Login History
                </button>
              </div>
            </div>
          </div>
        );

      case 'notifications':
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">Notification Preferences</h2>
              <p className="text-gray-600">Choose how you want to be notified about security events.</p>
            </div>

            <div className="space-y-4">
              {Object.entries(notificationSettings).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <h3 className="font-medium capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</h3>
                    <p className="text-sm text-gray-600">
                      {key === 'emailAlerts' && 'Receive email notifications for all activities'}
                      {key === 'scanComplete' && 'Get notified when scans are completed'}
                      {key === 'criticalFindings' && 'Alert for critical security findings'}
                      {key === 'weeklyReports' && 'Receive weekly summary reports'}
                      {key === 'slackNotifications' && 'Send notifications to Slack'}
                    </p>
                  </div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) => updateNotificationSetting(key as keyof NotificationSettings, e.target.checked)}
                      className="rounded"
                    />
                  </label>
                </div>
              ))}
            </div>
          </div>
        );

      case 'integrations':
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">Integrations</h2>
              <p className="text-gray-600">Connect with external services and tools.</p>
            </div>

            <div className="space-y-4">
              <div className="p-6 border rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <span className="text-blue-600 font-bold">S</span>
                    </div>
                    <div>
                      <h3 className="font-medium">Slack Integration</h3>
                      <p className="text-sm text-gray-600">Send notifications to Slack channels</p>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                    Configure
                  </button>
                </div>
              </div>

              <div className="p-6 border rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <span className="text-green-600 font-bold">T</span>
                    </div>
                    <div>
                      <h3 className="font-medium">Teams Integration</h3>
                      <p className="text-sm text-gray-600">Send notifications to Microsoft Teams</p>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                    Configure
                  </button>
                </div>
              </div>

              <div className="p-6 border rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                      <span className="text-purple-600 font-bold">W</span>
                    </div>
                    <div>
                      <h3 className="font-medium">Webhook Integration</h3>
                      <p className="text-sm text-gray-600">Send data to custom webhooks</p>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                    Configure
                  </button>
                </div>
              </div>
            </div>
          </div>
        );

      case 'preferences':
        return (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">System Preferences</h2>
              <p className="text-gray-600">Customize your experience with the security scanner.</p>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-4">Display Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span>Dark Mode</span>
                    <label className="flex items-center">
                      <input type="checkbox" className="rounded" />
                    </label>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Compact View</span>
                    <label className="flex items-center">
                      <input type="checkbox" className="rounded" />
                    </label>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-4">Data & Privacy</h3>
                <div className="space-y-4">
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">
                    Export My Data
                  </button>
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 ml-4">
                    Delete Account
                  </button>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-600 mt-2">Manage your account and application preferences</p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="w-64">
          <nav className="space-y-2">
            {SETTINGS_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'hover:bg-gray-50'
                }`}
              >
                <span>{tab.icon}</span>
                <span className="font-medium">{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="bg-white border rounded-lg p-6">
            {renderTabContent()}
          </div>
        </div>
      </div>
    </div>
  );
}