// ABOUTME: Zustand store for managing chat history with multiple conversations.
// ABOUTME: Persists threads to localStorage for cross-session access.

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatThread {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

interface ChatHistoryState {
  threads: ChatThread[];
  currentThreadId: string | null; // Currently selected/displayed thread
  liveThreadId: string | null; // Thread connected to active Chainlit session
  isOpen: boolean;

  // Actions
  createThread: () => string;
  selectThread: (id: string) => void;
  selectLiveThread: () => void; // Switch back to viewing live thread
  deleteThread: (id: string) => void;
  renameThread: (id: string, name: string) => void;
  addMessage: (threadId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  getCurrentThread: () => ChatThread | null;
  getLiveThread: () => ChatThread | null;
  isViewingLive: () => boolean;
  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
}

function generateId(): string {
  return `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function generateThreadName(content: string): string {
  // Generate name from first user message, truncated
  const cleaned = content.replace(/[*#`]/g, '').trim();
  if (cleaned.length <= 30) return cleaned;
  return cleaned.slice(0, 27) + '...';
}

export const useChatHistoryStore = create<ChatHistoryState>()(
  persist(
    (set, get) => ({
      threads: [],
      currentThreadId: null,
      liveThreadId: null,
      isOpen: false,

      createThread: () => {
        const id = generateId();
        const now = new Date().toISOString();
        const newThread: ChatThread = {
          id,
          name: 'New conversation',
          createdAt: now,
          updatedAt: now,
          messages: [],
        };
        set((state) => ({
          threads: [newThread, ...state.threads],
          currentThreadId: id,
          liveThreadId: id, // New thread is also the live thread
        }));
        return id;
      },

      selectThread: (id) => {
        // Selecting a thread makes it both current and live
        // This allows continuing any conversation
        set({ currentThreadId: id, liveThreadId: id });
      },

      selectLiveThread: () => {
        const { liveThreadId } = get();
        if (liveThreadId) {
          set({ currentThreadId: liveThreadId });
        }
      },

      deleteThread: (id) => {
        set((state) => {
          const filtered = state.threads.filter((t) => t.id !== id);
          // Don't allow deleting the live thread
          if (id === state.liveThreadId) {
            return state;
          }
          const newCurrentId =
            state.currentThreadId === id
              ? state.liveThreadId || (filtered.length > 0 ? filtered[0].id : null)
              : state.currentThreadId;
          return {
            threads: filtered,
            currentThreadId: newCurrentId,
          };
        });
      },

      renameThread: (id, name) => {
        set((state) => ({
          threads: state.threads.map((t) =>
            t.id === id ? { ...t, name, updatedAt: new Date().toISOString() } : t
          ),
        }));
      },

      addMessage: (threadId, message) => {
        const now = new Date().toISOString();

        set((state) => {
          const thread = state.threads.find((t) => t.id === threadId);
          if (!thread) return state;

          // Deduplicate: Check if this exact message content was just added (within last 2 seconds)
          const recentMessages = thread.messages.filter(
            (m) =>
              m.role === message.role &&
              m.content === message.content &&
              new Date(now).getTime() - new Date(m.timestamp).getTime() < 2000
          );
          if (recentMessages.length > 0) {
            // Duplicate detected, skip adding
            return state;
          }

          const fullMessage: ChatMessage = {
            ...message,
            id: generateMessageId(),
            timestamp: now,
          };

          // Check if this is the first USER message (for auto-naming)
          const hasUserMessage = thread.messages.some((m) => m.role === 'user');

          // Build updated thread
          const updatedThread = {
            ...thread,
            messages: [...thread.messages, fullMessage],
            updatedAt: now,
          };

          // Auto-name from first user message
          if (
            !hasUserMessage &&
            message.role === 'user' &&
            thread.name === 'New conversation'
          ) {
            updatedThread.name = generateThreadName(message.content);
          }

          return {
            threads: state.threads.map((t) =>
              t.id === threadId ? updatedThread : t
            ),
          };
        });
      },

      getCurrentThread: () => {
        const { threads, currentThreadId } = get();
        if (!currentThreadId) return null;
        return threads.find((t) => t.id === currentThreadId) || null;
      },

      getLiveThread: () => {
        const { threads, liveThreadId } = get();
        if (!liveThreadId) return null;
        return threads.find((t) => t.id === liveThreadId) || null;
      },

      isViewingLive: () => {
        const { currentThreadId, liveThreadId } = get();
        return currentThreadId === liveThreadId;
      },

      toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

      setOpen: (open) => set({ isOpen: open }),
    }),
    {
      name: 'clinical-codes-history',
      version: 1,
      migrate: (persistedState: unknown, version: number) => {
        const state = persistedState as ChatHistoryState;
        if (version === 0) {
          // Migration from v0: add liveThreadId if missing
          if (!state.liveThreadId && state.threads.length > 0) {
            state.liveThreadId = state.threads[0].id;
          }
          if (!state.currentThreadId && state.threads.length > 0) {
            state.currentThreadId = state.threads[0].id;
          }
        }
        return state;
      },
    }
  )
);

// Helper to group threads by time period
export function groupThreadsByTime(threads: ChatThread[]): Map<string, ChatThread[]> {
  const groups = new Map<string, ChatThread[]>();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  for (const thread of threads) {
    const threadDate = new Date(thread.updatedAt);
    let group: string;

    if (threadDate >= today) {
      group = 'Today';
    } else if (threadDate >= yesterday) {
      group = 'Yesterday';
    } else if (threadDate >= lastWeek) {
      group = 'Previous 7 Days';
    } else {
      group = 'Older';
    }

    const existing = groups.get(group) || [];
    groups.set(group, [...existing, thread]);
  }

  return groups;
}
