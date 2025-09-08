import React, { useState } from 'react';

interface Evidence {
  id: string;
  kind: string;
  file_url?: string;
  storage_url?: string;
  content_type?: string;
  size?: number;
  metadata?: Record<string, any>;
  created_at: string;
  correlation_id?: string;
  correlation_type?: string;
  tags?: string[];
}

interface EvidenceViewerProps {
  evidence: Evidence[];
  onDownload?: (evidence: Evidence) => void;
  onView?: (evidence: Evidence) => void;
}

const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  evidence,
  onDownload,
  onView
}) => {
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const getEvidenceIcon = (kind: string) => {
    switch (kind) {
      case 'screenshot':
        return <span className="text-blue-600 text-lg">📸</span>;
      case 'log':
        return <span className="text-gray-600 text-lg">📄</span>;
      case 'request_response':
        return <span className="text-green-600 text-lg">🌐</span>;
      case 'artifact':
        return <span className="text-purple-600 text-lg">📦</span>;
      default:
        return <span className="text-gray-600 text-lg">📄</span>;
    }
  };

  const getEvidenceTypeColor = (kind: string) => {
    switch (kind) {
      case 'screenshot':
        return 'bg-blue-100 text-blue-800';
      case 'log':
        return 'bg-gray-100 text-gray-800';
      case 'request_response':
        return 'bg-green-100 text-green-800';
      case 'artifact':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const filteredEvidence = evidence.filter(item => {
    if (filter === 'all') return true;
    return item.kind === filter;
  });

  const evidenceTypes = Array.from(new Set(evidence.map(item => item.kind)));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Evidence ({evidence.length})</h2>

        {/* Filter */}
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Filter:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border rounded px-3 py-1 text-sm"
          >
            <option value="all">All Types</option>
            {evidenceTypes.map(type => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Evidence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredEvidence.map((item) => (
          <div
            key={item.id}
            className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                {getEvidenceIcon(item.kind)}
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEvidenceTypeColor(item.kind)}`}>
                  {item.kind}
                </span>
              </div>
              <div className="flex gap-1">
                {item.file_url && (
                  <button
                    onClick={() => onView?.(item)}
                    className="p-1 text-gray-600 hover:text-gray-800"
                    title="View"
                  >
                    👁️
                  </button>
                )}
                {(item.file_url || item.storage_url) && (
                  <button
                    onClick={() => onDownload?.(item)}
                    className="p-1 text-gray-600 hover:text-gray-800"
                    title="Download"
                  >
                    ⬇️
                  </button>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="space-y-2">
              <div className="text-sm">
                <span className="font-medium">ID:</span> {item.id}
              </div>

              {item.size && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Size:</span> {formatFileSize(item.size)}
                </div>
              )}

              {item.content_type && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Type:</span> {item.content_type}
                </div>
              )}

              {item.correlation_id && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Correlation:</span> {item.correlation_id}
                </div>
              )}

              {item.tags && item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {item.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="text-xs text-gray-500 mt-2">
                {new Date(item.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredEvidence.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No evidence found matching the current filter.
        </div>
      )}

      {/* Evidence Detail Modal */}
      {selectedEvidence && (
        <EvidenceDetailModal
          evidence={selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          onDownload={onDownload}
        />
      )}
    </div>
  );
};

// Evidence Detail Modal Component
interface EvidenceDetailModalProps {
  evidence: Evidence;
  onClose: () => void;
  onDownload?: (evidence: Evidence) => void;
}

const EvidenceDetailModal: React.FC<EvidenceDetailModalProps> = ({
  evidence,
  onClose,
  onDownload
}) => {
  const renderEvidenceContent = (evidence: Evidence) => {
    switch (evidence.kind) {
      case 'screenshot':
        return evidence.file_url ? (
          <img
            src={evidence.file_url}
            alt="Screenshot"
            className="max-w-full max-h-96 object-contain"
          />
        ) : (
          <div className="text-center py-8 text-gray-500">
            Screenshot not available
          </div>
        );

      case 'log':
        return (
          <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96">
            {evidence.metadata?.inline || 'Log content not available'}
          </pre>
        );

      case 'request_response':
        const request = evidence.metadata?.request;
        const response = evidence.metadata?.response;

        return (
          <div className="space-y-4">
            {request && (
              <div>
                <h4 className="font-medium mb-2">Request</h4>
                <div className="bg-gray-100 p-3 rounded text-sm">
                  <div><strong>Method:</strong> {request.method}</div>
                  <div><strong>URL:</strong> {request.url}</div>
                  {request.headers && (
                    <div className="mt-2">
                      <strong>Headers:</strong>
                      <pre className="text-xs mt-1">{JSON.stringify(request.headers, null, 2)}</pre>
                    </div>
                  )}
                  {request.body && (
                    <div className="mt-2">
                      <strong>Body:</strong>
                      <pre className="text-xs mt-1">{request.body}</pre>
                    </div>
                  )}
                </div>
              </div>
            )}

            {response && (
              <div>
                <h4 className="font-medium mb-2">Response</h4>
                <div className="bg-gray-100 p-3 rounded text-sm">
                  <div><strong>Status:</strong> {response.status_code}</div>
                  {response.headers && (
                    <div className="mt-2">
                      <strong>Headers:</strong>
                      <pre className="text-xs mt-1">{JSON.stringify(response.headers, null, 2)}</pre>
                    </div>
                  )}
                  {response.body && (
                    <div className="mt-2">
                      <strong>Body:</strong>
                      <pre className="text-xs mt-1">{response.body}</pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="text-center py-8 text-gray-500">
            Preview not available for this evidence type
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Evidence Details - {evidence.id}
          </h3>
          <div className="flex items-center gap-2">
            {onDownload && (
              <button
                onClick={() => onDownload(evidence)}
                className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                Download
              </button>
            )}
            <button
              onClick={onClose}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-auto max-h-[calc(90vh-120px)]">
          {renderEvidenceContent(evidence)}
        </div>
      </div>
    </div>
  );
};

export default EvidenceViewer;