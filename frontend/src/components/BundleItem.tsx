// ABOUTME: Single item in the bundle sidebar with monochrome styling.
// ABOUTME: Shows code, system with icon, and display name with remove button.

import { X, Stethoscope, Pill, FlaskConical, ClipboardList, Ruler, Dna } from 'lucide-react';
import { useBundleStore } from '../stores/bundleStore';
import type { BundleItem as BundleItemType } from '../types';

interface Props {
  item: BundleItemType;
}

const SYSTEM_ICONS: Record<string, typeof Stethoscope> = {
  'ICD-10-CM': Stethoscope,
  'RxTerms': Pill,
  'LOINC': FlaskConical,
  'HCPCS': ClipboardList,
  'UCUM': Ruler,
  'HPO': Dna,
};

export function BundleItem({ item }: Props) {
  const { removeItem } = useBundleStore();

  const handleRemove = () => {
    removeItem(item.code, item.system);
  };

  const SystemIcon = SYSTEM_ICONS[item.system] || ClipboardList;

  return (
    <div className="group flex items-start gap-3 p-3 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-softer)] rounded-lg transition-colors">
      <div className="flex-1 min-w-0">
        {/* Code */}
        <code className="text-sm font-mono font-semibold text-[var(--accent-primary)]">
          {item.code}
        </code>

        {/* System badge with icon */}
        <div className="flex items-center gap-1.5 mt-1">
          <SystemIcon className="w-3 h-3 text-[var(--text-muted)]" />
          <span className="text-xs text-[var(--text-muted)]">
            {item.system}
          </span>
        </div>

        {/* Display text */}
        <p
          className="text-xs text-[var(--text-secondary)] truncate mt-1"
          title={item.display}
        >
          {item.display}
        </p>
      </div>

      {/* Remove button */}
      <button
        onClick={handleRemove}
        className="p-1 text-[var(--text-muted)] hover:text-[var(--error)] opacity-0 group-hover:opacity-100 transition-all rounded"
        title="Remove from bundle"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
