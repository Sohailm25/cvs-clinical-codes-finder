// ABOUTME: Application header with CVS branding and navigation controls.
// ABOUTME: Provides sidebar toggles and theme switcher with refined styling.

import { Menu, Package } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from '../hooks/useTheme';

interface HeaderProps {
  onToggleHistory?: () => void;
  onToggleBundle?: () => void;
  historyOpen?: boolean;
  bundleOpen?: boolean;
  bundleCount?: number;
}

export function Header({
  onToggleHistory,
  onToggleBundle,
  historyOpen,
  bundleOpen,
  bundleCount = 0,
}: HeaderProps) {
  const { isDark } = useTheme();

  // Bundle button colors when open
  const bundleOpenBg = isDark ? '#44b4e7' : '#17447c';
  const bundleOpenText = isDark ? '#111827' : '#FFFFFF';

  return (
    <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-default)] shadow-theme-sm transition-theme">
      <div className="flex items-center justify-between h-14 px-4">
        {/* Left section - History toggle and branding */}
        <div className="flex items-center gap-4">
          {onToggleHistory && (
            <button
              onClick={onToggleHistory}
              className={`p-2 rounded-lg transition-colors ${
                historyOpen
                  ? 'bg-[var(--accent-soft)] text-[var(--accent-primary)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-softer)]'
              }`}
              title={historyOpen ? 'Close chat history' : 'View chat history'}
              aria-label="Toggle chat history"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          {/* CVS Logo */}
          <div className="flex items-center gap-3">
            <img
              src="/cvs-logo.png"
              alt="CVS"
              className="h-7 w-auto"
            />
            <div className="h-5 w-px bg-[var(--border-default)]" />
            <h1 className="text-base font-semibold text-[var(--text-primary)]">
              Clinical Codes Finder
            </h1>
          </div>
        </div>

        {/* Right section - Theme toggle and Bundle */}
        <div className="flex items-center gap-2">
          <ThemeToggle />

          {onToggleBundle && (
            <button
              onClick={onToggleBundle}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                bundleOpen
                  ? ''
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-softer)]'
              }`}
              style={bundleOpen ? { backgroundColor: bundleOpenBg, color: bundleOpenText } : undefined}
              title={bundleOpen
                ? 'Close code bundle'
                : bundleCount > 0
                  ? `View code bundle (${bundleCount} code${bundleCount !== 1 ? 's' : ''})`
                  : 'View code bundle'
              }
              aria-label="Toggle code bundle"
            >
              <Package className="w-5 h-5" />
              {bundleCount > 0 && (
                <span
                  className="text-xs font-medium min-w-[1.25rem] text-center px-1.5 py-0.5 rounded-full"
                  style={bundleOpen
                    ? { color: bundleOpenText }
                    : { backgroundColor: '#CC0000', color: '#FFFFFF' }
                  }
                >
                  {bundleCount}
                </span>
              )}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
