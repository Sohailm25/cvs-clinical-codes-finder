// ABOUTME: Clean code result card with confidence progress bar.
// ABOUTME: Displays individual clinical codes in a scannable, professional format.

import { useState } from 'react';
import { Plus, Check, Copy } from 'lucide-react';
import { useBundleStore } from '../stores/bundleStore';
import { useToastStore } from '../stores/toastStore';

export interface CodeResult {
  code: string;
  display: string;
  confidence: number;
  system: string;
  metadata?: Record<string, string>;
  parentCode?: string;
  parentDisplay?: string;
}

interface CodeResultCardProps {
  result: CodeResult;
  showHierarchy?: boolean;
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
        <div
          className="h-full bg-[var(--accent-primary)] rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-[var(--text-muted)] font-medium tabular-nums w-8">
        {pct}%
      </span>
    </div>
  );
}

export function CodeResultCard({ result, showHierarchy = false }: CodeResultCardProps) {
  const { addItem, hasItem } = useBundleStore();
  const { addToast } = useToastStore();
  const isInBundle = hasItem(result.code, result.system);
  const [copied, setCopied] = useState(false);

  const handleAddToBundle = () => {
    if (!isInBundle) {
      addItem({
        code: result.code,
        system: result.system,
        display: result.display,
      });
      addToast(`Added ${result.code} to bundle`, 'success');
    }
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(result.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="group flex items-start gap-3 p-4 hover:bg-[var(--accent-softer)] transition-colors">
      {/* Add to bundle button */}
      <button
        onClick={handleAddToBundle}
        disabled={isInBundle}
        className={`mt-0.5 p-1.5 rounded-lg transition-all flex-shrink-0 ${
          isInBundle
            ? 'bg-[var(--success-soft)] text-[var(--success)] cursor-default'
            : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:bg-[var(--accent-primary)] hover:text-white'
        }`}
        title={isInBundle ? 'Already in bundle' : 'Add to bundle'}
      >
        {isInBundle ? (
          <Check className="w-4 h-4" />
        ) : (
          <Plus className="w-4 h-4" />
        )}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Code and display text */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <code className="text-sm font-mono font-semibold text-[var(--accent-primary)]">
              {result.code}
            </code>
            <p className="text-sm text-[var(--text-primary)] mt-0.5 leading-snug">
              {result.display}
            </p>
          </div>
          {/* Copy button */}
          <button
            onClick={handleCopyCode}
            className={`p-1.5 rounded-lg transition-all flex-shrink-0 ${
              copied
                ? 'bg-[var(--success-soft)] text-[var(--success)]'
                : 'opacity-0 group-hover:opacity-100 bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-primary)]'
            }`}
            title={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Confidence bar */}
        <ConfidenceBar confidence={result.confidence} />

        {/* Metadata */}
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
            {Object.entries(result.metadata).slice(0, 3).map(([key, value]) => (
              <span key={key} className="text-[var(--text-muted)]">
                <span className="text-[var(--text-secondary)]">{key}:</span>{' '}
                {value}
              </span>
            ))}
          </div>
        )}

        {/* Parent hierarchy */}
        {showHierarchy && result.parentCode && (
          <div className="text-xs text-[var(--text-muted)]">
            <span className="text-[var(--text-secondary)]">Parent:</span>{' '}
            <code className="px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded font-mono text-[var(--text-secondary)]">
              {result.parentCode}
            </code>{' '}
            {result.parentDisplay}
          </div>
        )}
      </div>
    </div>
  );
}

export function parseCodeResults(markdown: string): { summary: string; systems: Map<string, CodeResult[]> } {
  const lines = markdown.split('\n');
  const systems = new Map<string, CodeResult[]>();
  let currentSystem = '';
  let summary = '';
  let inResults = false;
  let lastResult: CodeResult | null = null;

  for (const line of lines) {
    const systemMatch = line.match(/^###\s+(.+?)\s+\(\d+\s+results?\)/);
    if (systemMatch) {
      currentSystem = systemMatch[1];
      systems.set(currentSystem, []);
      inResults = true;
      lastResult = null;
      continue;
    }

    // Check for parent hierarchy line: "  - > Parent: `E11` Type 2 diabetes"
    const parentMatch = line.match(/^\s*-\s*>\s*Parent:\s*`([^`]+)`\s*(.+)$/);
    if (parentMatch && lastResult) {
      lastResult.parentCode = parentMatch[1];
      lastResult.parentDisplay = parentMatch[2].trim();
      continue;
    }

    if (currentSystem && systems.has(currentSystem) && line.trim().startsWith('-')) {
      const codeMatch = line.match(/`([^`]+)`/);
      const displayMatch = line.match(/\*\*(.+?)\*\*/);
      const pctMatch = line.match(/(\d+)%/);

      if (codeMatch && displayMatch) {
        const results = systems.get(currentSystem)!;
        const result: CodeResult = {
          code: codeMatch[1],
          display: displayMatch[1],
          confidence: pctMatch ? parseInt(pctMatch[1], 10) / 100 : 0.5,
          system: currentSystem,
        };
        results.push(result);
        lastResult = result;
        continue;
      }
    }

    if (!inResults && line.trim() && !line.startsWith('---') && !line.startsWith('*Searched:')) {
      summary += (summary ? '\n' : '') + line;
    }
  }

  return { summary, systems };
}

export function hasCodeResults(content: string): boolean {
  return /###\s+.+?\s+\(\d+\s+results?\)/.test(content);
}
