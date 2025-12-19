// ABOUTME: Chat input area with send button and settings.
// ABOUTME: Handles message submission to the Chainlit backend.

import { useState, useRef, useEffect } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { useChatInteract, useChatData } from '@chainlit/react-client';
import { Send, Loader2 } from 'lucide-react';
import { SettingsPopup } from './SettingsPopup';

export function InputArea() {
  const [input, setInput] = useState('');
  const { sendMessage } = useChatInteract();
  const { loading } = useChatData();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Global keyboard shortcut: Cmd/Ctrl + K to focus search
  useEffect(() => {
    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    sendMessage({
      name: 'User',
      type: 'user_message',
      output: input.trim(),
    });
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 border-t border-[var(--border-default)] bg-[var(--bg-secondary)] transition-theme"
    >
      <div className="flex gap-3 items-end max-w-4xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search for clinical codes..."
            disabled={loading}
            rows={1}
            className="w-full px-4 py-3 bg-[var(--bg-primary)] border border-[var(--border-default)] rounded-xl
              text-[var(--text-primary)] placeholder-[var(--text-muted)]
              focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent
              disabled:opacity-50 disabled:cursor-not-allowed
              resize-none transition-theme"
          />
        </div>

        <SettingsPopup />

        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="p-3 bg-cvs-navy hover:bg-cvs-navy-hover dark:bg-cvs-blue dark:hover:bg-cvs-blue-hover
            disabled:bg-[var(--bg-tertiary)] disabled:cursor-not-allowed
            text-white dark:text-gray-900 rounded-xl transition-colors
            shadow-theme-sm hover:shadow-theme-md disabled:shadow-none"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      <p className="text-xs text-[var(--text-muted)] mt-2 text-center">
        Press Enter to send, Shift+Enter for new line
        <span className="mx-2">·</span>
        <kbd className="px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded text-[var(--text-secondary)] font-mono text-[10px]">⌘K</kbd>
        {' '}to focus search
      </p>
    </form>
  );
}
