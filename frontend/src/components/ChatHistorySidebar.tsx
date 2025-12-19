// ABOUTME: Left sidebar displaying chat history with multiple conversations.
// ABOUTME: Allows creating, selecting, renaming, and deleting conversation threads.

import { useState } from 'react';
import { Plus, MessageSquare, Trash2, Pencil, X, Check } from 'lucide-react';
import {
  useChatHistoryStore,
  groupThreadsByTime,
  type ChatThread,
} from '../stores/chatHistoryStore';
import { useTheme } from '../hooks/useTheme';

interface ChatHistorySidebarProps {
  onClose?: () => void;
  onNewChat?: () => void;
  onSelectThread?: (threadId: string) => void;
}

function ThreadItem({
  thread,
  isSelected,
  onSelect,
  onDelete,
  onRename,
}: {
  thread: ChatThread;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (name: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(thread.name);

  const handleSubmitRename = () => {
    if (editName.trim()) {
      onRename(editName.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
        isSelected
          ? 'bg-[var(--accent-soft)] border-l-2 border-[var(--accent-primary)]'
          : 'hover:bg-[var(--accent-softer)]'
      }`}
      onClick={() => !isEditing && onSelect()}
    >
      <MessageSquare className={`w-4 h-4 flex-shrink-0 ${
        isSelected ? 'text-[var(--accent-primary)]' : 'text-[var(--text-muted)]'
      }`} />

      {isEditing ? (
        <div className="flex-1 flex items-center gap-1">
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSubmitRename();
              if (e.key === 'Escape') setIsEditing(false);
            }}
            className="flex-1 bg-[var(--bg-primary)] text-sm px-2 py-1 rounded border border-[var(--border-default)] focus:outline-none focus:border-[var(--accent-primary)] text-[var(--text-primary)]"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleSubmitRename();
            }}
            className="p-1 hover:bg-[var(--accent-softer)] rounded"
          >
            <Check className="w-3 h-3 text-[var(--success)]" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(false);
            }}
            className="p-1 hover:bg-[var(--accent-softer)] rounded"
          >
            <X className="w-3 h-3 text-[var(--text-muted)]" />
          </button>
        </div>
      ) : (
        <>
          <span className={`flex-1 text-sm truncate ${
            isSelected ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'
          }`}>
            {thread.name}
          </span>
          <div className="hidden group-hover:flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditName(thread.name);
                setIsEditing(true);
              }}
              className="p-1 hover:bg-[var(--bg-tertiary)] rounded"
              title="Rename"
            >
              <Pencil className="w-3 h-3 text-[var(--text-muted)]" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1 hover:bg-[var(--error-soft)] rounded"
              title="Delete"
            >
              <Trash2 className="w-3 h-3 text-[var(--text-muted)] hover:text-[var(--error)]" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function ChatHistorySidebar({
  onClose,
  onNewChat,
  onSelectThread,
}: ChatHistorySidebarProps) {
  const {
    threads,
    currentThreadId,
    selectThread,
    deleteThread,
    renameThread,
    getCurrentThread,
  } = useChatHistoryStore();
  const { isDark } = useTheme();

  const groupedThreads = groupThreadsByTime(threads);
  const groupOrder = ['Today', 'Yesterday', 'Previous 7 Days', 'Older'];

  const currentThread = getCurrentThread();
  const canCreateNewChat = currentThread ? currentThread.messages.length > 0 : true;

  // Button colors: Navy in light mode, Blue in dark mode
  const buttonBg = isDark ? '#44b4e7' : '#17447c';
  const buttonHoverBg = isDark ? '#5bc4f0' : '#1a5090';
  const buttonText = isDark ? '#111827' : '#FFFFFF';

  const handleNewChat = () => {
    if (!canCreateNewChat) return;
    onNewChat?.();
  };

  const handleSelectThread = (threadId: string) => {
    selectThread(threadId);
    onSelectThread?.(threadId);
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-secondary)] transition-theme">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-default)]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-[var(--text-primary)]">History</h2>
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
        <button
          onClick={handleNewChat}
          disabled={!canCreateNewChat}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg transition-colors font-medium ${
            canCreateNewChat
              ? 'shadow-theme-sm hover:shadow-theme-md'
              : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] cursor-not-allowed'
          }`}
          style={canCreateNewChat ? { backgroundColor: buttonBg, color: buttonText } : undefined}
          onMouseEnter={(e) => canCreateNewChat && (e.currentTarget.style.backgroundColor = buttonHoverBg)}
          onMouseLeave={(e) => canCreateNewChat && (e.currentTarget.style.backgroundColor = buttonBg)}
          title={canCreateNewChat ? 'Start a new conversation' : 'Send a message first'}
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto p-3">
        {threads.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-12 h-12 rounded-full bg-[var(--accent-softer)] flex items-center justify-center mb-3">
              <MessageSquare className="w-6 h-6 text-[var(--accent-primary)]" />
            </div>
            <p className="text-sm font-medium text-[var(--text-secondary)]">
              No conversations yet
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Start typing to begin
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {groupOrder.map((group) => {
              const groupThreads = groupedThreads.get(group);
              if (!groupThreads || groupThreads.length === 0) return null;

              return (
                <div key={group}>
                  <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider px-3 mb-2">
                    {group}
                  </h3>
                  <div className="space-y-1">
                    {groupThreads.map((thread) => (
                      <ThreadItem
                        key={thread.id}
                        thread={thread}
                        isSelected={thread.id === currentThreadId}
                        onSelect={() => handleSelectThread(thread.id)}
                        onDelete={() => deleteThread(thread.id)}
                        onRename={(name) => renameThread(thread.id, name)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
