// ABOUTME: Main chat container with message list and input area.
// ABOUTME: Handles the layout for the chat interface.

import { useChatData } from '@chainlit/react-client';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { Loader2 } from 'lucide-react';

export function ChatContainer() {
  const { connected } = useChatData();

  if (!connected) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[var(--bg-primary)] transition-theme">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-[var(--accent-primary)] animate-spin mx-auto mb-3" />
          <p className="text-[var(--text-muted)]">Connecting to server...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--bg-primary)] transition-theme">
      <MessageList />
      <InputArea />
    </div>
  );
}
