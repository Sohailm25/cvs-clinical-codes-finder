// ABOUTME: Main application component with three-column layout.
// ABOUTME: Contains chat history sidebar, main chat area, and bundle sidebar.

import { useEffect, useCallback } from 'react';
import { useChatSession, messagesState } from '@chainlit/react-client';
import { useSetRecoilState } from 'recoil';
import { ChatContainer } from './components/ChatContainer';
import { BundleSidebar } from './components/BundleSidebar';
import { ChatHistorySidebar } from './components/ChatHistorySidebar';
import { Header } from './components/Header';
import { ToastContainer } from './components/Toast';
import { useBundleStore } from './stores/bundleStore';
import { useChatHistoryStore } from './stores/chatHistoryStore';
import { useChatHistorySync } from './hooks/useChatHistorySync';
import { useTheme } from './hooks/useTheme';

function App() {
  const { connect, disconnect } = useChatSession();
  const setMessages = useSetRecoilState(messagesState);
  const { isOpen: bundleOpen, items, toggleOpen: toggleBundle } = useBundleStore();
  const {
    isOpen: historyOpen,
    toggleOpen: toggleHistory,
    createThread,
    selectThread,
    getLiveThread,
    currentThreadId,
  } = useChatHistoryStore();

  // Initialize theme on mount
  useTheme();

  // Sync Chainlit messages to our history store
  const { resetTracking, pauseSync } = useChatHistorySync();

  useEffect(() => {
    // Connect to Chainlit backend on mount
    connect({ userEnv: {} });
  }, [connect]);

  const handleNewChat = useCallback(() => {
    const liveThread = getLiveThread();

    // Don't create new thread if live thread has no messages
    if (liveThread && liveThread.messages.length === 0) {
      return;
    }

    // Disconnect and reconnect to get fresh backend state
    disconnect();
    setMessages([]);
    resetTracking();

    // Create new thread and reconnect
    createThread();
    connect({ userEnv: {} });
  }, [getLiveThread, disconnect, setMessages, resetTracking, createThread, connect]);

  const handleSelectThread = useCallback((threadId: string) => {
    // If clicking the already-selected thread, do nothing
    if (threadId === currentThreadId) return;

    // Pause syncing BEFORE changing thread to prevent race conditions
    pauseSync();
    // Clear live Chainlit messages when switching threads
    setMessages([]);
    selectThread(threadId);
  }, [currentThreadId, selectThread, setMessages, pauseSync]);

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-primary)] transition-theme">
      <Header
        onToggleHistory={toggleHistory}
        onToggleBundle={toggleBundle}
        historyOpen={historyOpen}
        bundleOpen={bundleOpen}
        bundleCount={items.length}
      />
      <div className="flex flex-1 overflow-hidden">
        {/* History sidebar - slides in/out, pushes content */}
        <div
          className={`flex-shrink-0 bg-[var(--bg-secondary)] border-r border-[var(--border-default)] transition-all duration-300 ease-in-out overflow-hidden ${
            historyOpen ? 'w-72' : 'w-0'
          }`}
        >
          <div className="w-72 h-full">
            <ChatHistorySidebar
              onClose={toggleHistory}
              onNewChat={handleNewChat}
              onSelectThread={handleSelectThread}
            />
          </div>
        </div>

        {/* Main chat area - click to close sidebars */}
        <div
          className="flex-1 flex flex-col min-w-0"
          onClick={() => {
            if (historyOpen) toggleHistory();
          }}
        >
          <ChatContainer />
        </div>

        {/* Bundle sidebar - slides in/out, pushes content */}
        <div
          className={`flex-shrink-0 bg-[var(--bg-secondary)] border-l border-[var(--border-default)] transition-all duration-300 ease-in-out overflow-hidden ${
            bundleOpen ? 'w-80' : 'w-0'
          }`}
        >
          <div className="w-80 h-full">
            <BundleSidebar onClose={toggleBundle} />
          </div>
        </div>
      </div>

      {/* Toast notifications */}
      <ToastContainer />
    </div>
  );
}

export default App;
