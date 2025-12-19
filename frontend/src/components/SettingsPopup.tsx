// ABOUTME: Compact settings popup with toggle switches.
// ABOUTME: Provides inline settings for search configuration.

import { useState, useRef, useEffect } from 'react';
import { Settings, X } from 'lucide-react';
import { useChatInteract, useChatData } from '@chainlit/react-client';

interface SettingToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function SettingToggle({ label, description, checked, onChange }: SettingToggleProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 w-9 h-5 rounded-full transition-colors ${
          checked ? 'bg-[var(--accent-primary)]' : 'bg-[var(--border-default)]'
        }`}
      >
        <div
          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${
            checked ? 'left-[18px]' : 'left-0.5'
          }`}
        />
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
          {label}
        </p>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          {description}
        </p>
      </div>
    </label>
  );
}

export function SettingsPopup() {
  const [isOpen, setIsOpen] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);
  const { updateChatSettings } = useChatInteract();
  const { chatSettingsValue } = useChatData();

  const [localSettings, setLocalSettings] = useState({
    clarification_enabled: true,
    multi_hop_enabled: false,
    show_hierarchy: true,
  });

  useEffect(() => {
    if (chatSettingsValue) {
      setLocalSettings(chatSettingsValue);
    }
  }, [chatSettingsValue]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSettingChange = (key: string, value: boolean) => {
    const newSettings = {
      ...localSettings,
      [key]: value,
    };
    setLocalSettings(newSettings);

    try {
      updateChatSettings(newSettings);
    } catch (e) {
      console.log('Settings update:', newSettings);
    }
  };

  return (
    <div className="relative" ref={popupRef}>
      {/* Settings button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2.5 rounded-xl transition-colors ${
          isOpen
            ? 'bg-[var(--accent-soft)] text-[var(--accent-primary)]'
            : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-softer)]'
        }`}
        title="Search settings"
      >
        <Settings className="w-5 h-5" />
      </button>

      {/* Popup */}
      {isOpen && (
        <div className="absolute right-0 bottom-full mb-2 w-72 bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-xl shadow-theme-lg z-50 transition-theme">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)]">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Search Settings</h3>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Settings */}
          <div className="p-4 space-y-4">
            <SettingToggle
              label="Smart Clarification"
              description="Ask follow-up questions for ambiguous queries"
              checked={localSettings.clarification_enabled}
              onChange={(v) => handleSettingChange('clarification_enabled', v)}
            />

            <SettingToggle
              label="Multi-hop Search"
              description="Search related terms for broader results"
              checked={localSettings.multi_hop_enabled}
              onChange={(v) => handleSettingChange('multi_hop_enabled', v)}
            />

            <SettingToggle
              label="Show Hierarchy"
              description="Display parent codes for ICD-10 results"
              checked={localSettings.show_hierarchy}
              onChange={(v) => handleSettingChange('show_hierarchy', v)}
            />
          </div>

          {/* Footer */}
          <div className="px-4 py-2 bg-[var(--bg-tertiary)] border-t border-[var(--border-subtle)] rounded-b-xl">
            <p className="text-xs text-[var(--text-muted)]">
              Settings apply to new searches
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
