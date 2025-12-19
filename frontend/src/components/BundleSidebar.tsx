// ABOUTME: Right sidebar displaying the current code bundle.
// ABOUTME: Allows viewing, removing, and exporting bundled codes.

import { Package, Trash2, Download, X } from 'lucide-react';
import { useBundleStore, exportBundleToCSV } from '../stores/bundleStore';
import { BundleItem } from './BundleItem';

interface BundleSidebarProps {
  onClose?: () => void;
}

export function BundleSidebar({ onClose }: BundleSidebarProps) {
  const { items, clear } = useBundleStore();

  const handleExport = () => {
    exportBundleToCSV(items);
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-secondary)] transition-theme">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-default)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-[var(--text-primary)]" />
            <h2 className="font-semibold text-[var(--text-primary)]">
              Code Bundle
            </h2>
            {items.length > 0 && (
              <span className="px-2 py-0.5 text-xs rounded-full font-medium"
                style={{ backgroundColor: '#CC0000', color: '#FFFFFF' }}>
                {items.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {items.length > 0 && (
              <button
                onClick={clear}
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--error)] hover:bg-[var(--error-soft)] rounded-lg transition-colors"
                title="Clear bundle"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-softer)] rounded-lg transition-colors"
                title="Close sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Bundle items */}
      <div className="flex-1 overflow-y-auto p-3">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-12 h-12 rounded-full bg-[var(--accent-softer)] flex items-center justify-center mb-3">
              <Package className="w-6 h-6 text-[var(--accent-primary)]" />
            </div>
            <p className="text-sm font-medium text-[var(--text-secondary)]">
              No codes in bundle
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Click the + button on search results to add codes
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <BundleItem
                key={`${item.system}-${item.code}`}
                item={item}
              />
            ))}
          </div>
        )}
      </div>

      {/* Export button */}
      {items.length > 0 && (
        <div className="p-4 border-t border-[var(--border-default)]">
          <button
            onClick={handleExport}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg transition-colors font-medium shadow-theme-sm hover:shadow-theme-md"
            style={{ backgroundColor: '#CC0000', color: '#FFFFFF' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#B80000'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#CC0000'}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      )}
    </div>
  );
}
