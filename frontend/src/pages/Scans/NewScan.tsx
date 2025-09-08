import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTargets, useTriggerScan } from '@api/hooks/resources';

type ScanConfig = {
  target: number | '';
  mode: string;
  scanType: string;
  depth: string;
  includeSubdomains: boolean;
  scheduleType: 'immediate' | 'scheduled' | 'recurring';
  scheduleTime?: string;
  recurringInterval?: string;
};

const STEPS = [
  { id: 1, title: 'Target Selection', description: 'Choose target to scan' },
  { id: 2, title: 'Scan Configuration', description: 'Configure scan parameters' },
  { id: 3, title: 'Schedule Options', description: 'Set timing preferences' },
  { id: 4, title: 'Review & Confirm', description: 'Review and start scan' }
];

export default function NewScan() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<ScanConfig>({
    target: '',
    mode: 'quick',
    scanType: 'comprehensive',
    depth: 'medium',
    includeSubdomains: false,
    scheduleType: 'immediate'
  });

  const trigger = useTriggerScan();
  const { data: targets, isLoading } = useTargets({ page_size: 100 });

  const updateConfig = (updates: Partial<ScanConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  };

  const nextStep = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const onSubmit = async () => {
    if (!config.target) return;
    try {
      await trigger.mutateAsync({
        target: Number(config.target),
        mode: config.mode
      });
      navigate('/scans');
    } catch {
      alert('Failed to trigger scan');
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <h2 className="text-lg font-medium">Select Target</h2>
            <p className="text-gray-600">Choose the target you want to scan for vulnerabilities.</p>

            <div className="space-y-3">
              {isLoading ? (
                <div className="text-center py-8">Loading targets...</div>
              ) : (
                targets?.results?.map((target) => (
                  <label key={target.id} className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input
                      type="radio"
                      name="target"
                      value={target.id}
                      checked={config.target === target.id}
                      onChange={(e) => updateConfig({ target: Number(e.target.value) })}
                      className="text-blue-600"
                    />
                    <div>
                      <div className="font-medium">{target.name}</div>
                      <div className="text-sm text-gray-600">{target.address}</div>
                      {target.type && <div className="text-xs text-gray-500">Type: {target.type}</div>}
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Scan Configuration</h2>
            <p className="text-gray-600">Configure the parameters for your security scan.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Scan Mode</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={config.mode}
                  onChange={(e) => updateConfig({ mode: e.target.value })}
                >
                  <option value="quick">Quick Scan</option>
                  <option value="full">Full Scan</option>
                  <option value="deep">Deep Scan</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Scan Type</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={config.scanType}
                  onChange={(e) => updateConfig({ scanType: e.target.value })}
                >
                  <option value="comprehensive">Comprehensive</option>
                  <option value="web-only">Web Only</option>
                  <option value="api-only">API Only</option>
                  <option value="network-only">Network Only</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Depth</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={config.depth}
                  onChange={(e) => updateConfig({ depth: e.target.value })}
                >
                  <option value="light">Light</option>
                  <option value="medium">Medium</option>
                  <option value="deep">Deep</option>
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="subdomains"
                  checked={config.includeSubdomains}
                  onChange={(e) => updateConfig({ includeSubdomains: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="subdomains" className="text-sm text-gray-700">
                  Include subdomains
                </label>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Schedule Options</h2>
            <p className="text-gray-600">Choose when you want this scan to run.</p>

            <div className="space-y-4">
              <div>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="schedule"
                    value="immediate"
                    checked={config.scheduleType === 'immediate'}
                    onChange={(e) => updateConfig({ scheduleType: 'immediate' as const })}
                  />
                  <span>Run immediately</span>
                </label>
              </div>

              <div>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="schedule"
                    value="scheduled"
                    checked={config.scheduleType === 'scheduled'}
                    onChange={(e) => updateConfig({ scheduleType: 'scheduled' as const })}
                  />
                  <span>Schedule for later</span>
                </label>
                {config.scheduleType === 'scheduled' && (
                  <input
                    type="datetime-local"
                    className="mt-2 w-full border rounded px-3 py-2"
                    value={config.scheduleTime || ''}
                    onChange={(e) => updateConfig({ scheduleTime: e.target.value })}
                  />
                )}
              </div>

              <div>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="schedule"
                    value="recurring"
                    checked={config.scheduleType === 'recurring'}
                    onChange={(e) => updateConfig({ scheduleType: 'recurring' as const })}
                  />
                  <span>Recurring scan</span>
                </label>
                {config.scheduleType === 'recurring' && (
                  <select
                    className="mt-2 w-full border rounded px-3 py-2"
                    value={config.recurringInterval || ''}
                    onChange={(e) => updateConfig({ recurringInterval: e.target.value })}
                  >
                    <option value="">Select interval</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                )}
              </div>
            </div>
          </div>
        );

      case 4:
        const selectedTarget = targets?.results?.find(t => t.id === config.target);
        return (
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Review & Confirm</h2>
            <p className="text-gray-600">Please review your scan configuration before starting.</p>

            <div className="bg-gray-50 p-6 rounded-lg space-y-4">
              <div>
                <h3 className="font-medium text-gray-900">Target</h3>
                <p className="text-gray-600">{selectedTarget?.name} — {selectedTarget?.address}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="font-medium text-gray-900">Scan Mode</h3>
                  <p className="text-gray-600 capitalize">{config.mode}</p>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Scan Type</h3>
                  <p className="text-gray-600 capitalize">{config.scanType.replace('-', ' ')}</p>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Depth</h3>
                  <p className="text-gray-600 capitalize">{config.depth}</p>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Schedule</h3>
                  <p className="text-gray-600 capitalize">{config.scheduleType}</p>
                </div>
              </div>

              {config.includeSubdomains && (
                <div className="text-sm text-gray-600">
                  ✓ Include subdomains
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-2">New Security Scan</h1>
        <p className="text-gray-600">Configure and launch a new vulnerability scan</p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {STEPS.map((step) => (
            <div key={step.id} className="flex items-center">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                step.id <= currentStep
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {step.id}
              </div>
              <div className="ml-3 hidden sm:block">
                <div className={`text-sm font-medium ${
                  step.id <= currentStep ? 'text-blue-600' : 'text-gray-500'
                }`}>
                  {step.title}
                </div>
                <div className="text-xs text-gray-500">{step.description}</div>
              </div>
              {step.id < STEPS.length && (
                <div className={`w-12 h-0.5 mx-4 ${
                  step.id < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white border rounded-lg p-6 mb-6">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          type="button"
          onClick={prevStep}
          disabled={currentStep === 1}
          className="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Previous
        </button>

        {currentStep < STEPS.length ? (
          <button
            type="button"
            onClick={nextStep}
            disabled={currentStep === 1 && !config.target}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700"
          >
            Next
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={trigger.isPending}
            className="px-6 py-2 bg-green-600 text-white rounded disabled:opacity-50 hover:bg-green-700"
          >
            {trigger.isPending ? 'Starting Scan...' : 'Start Scan'}
          </button>
        )}
      </div>
    </div>
  );
}