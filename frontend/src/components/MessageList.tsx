// ABOUTME: Scrollable list of chat messages.
// ABOUTME: Auto-scrolls to newest message and renders messages with actions.

import { useEffect, useRef, useState } from 'react';
import { useChatMessages, useChatData } from '@chainlit/react-client';
import type { IStep } from '@chainlit/react-client';
import { Message } from './Message';
import { HistoricalMessage } from './HistoricalMessage';
import { SkeletonLoading } from './Skeleton';
import { useChatHistoryStore } from '../stores/chatHistoryStore';

function flattenSteps(steps: IStep[]): IStep[] {
  const result: IStep[] = [];

  for (const step of steps) {
    if (step.output && step.output.trim()) {
      result.push(step);
    }
    if (step.steps && step.steps.length > 0) {
      result.push(...flattenSteps(step.steps));
    }
  }

  return result;
}

function isWelcomeMessage(content: string): boolean {
  return content.includes('What clinical code are you looking for?') ||
         (content.includes('Search across') && content.includes('ICD-10-CM'));
}

export function MessageList() {
  const { messages } = useChatMessages();
  const { actions, loading } = useChatData();
  const bottomRef = useRef<HTMLDivElement>(null);
  const { getCurrentThread, currentThreadId } = useChatHistoryStore();

  const currentThread = getCurrentThread();

  // Track if we're in the "just switched" window
  const prevThreadIdRef = useRef<string | null>(currentThreadId);
  const [isInSwitchWindow, setIsInSwitchWindow] = useState(false);

  useEffect(() => {
    if (prevThreadIdRef.current !== currentThreadId) {
      setIsInSwitchWindow(true);
      prevThreadIdRef.current = currentThreadId;
      const timer = setTimeout(() => setIsInSwitchWindow(false), 300);
      return () => clearTimeout(timer);
    }
  }, [currentThreadId]);

  // Check if thread was created recently (within last 2 seconds)
  // This catches the case where we create a new thread and haven't switched yet
  const isNewlyCreatedThread = currentThread &&
    currentThread.messages.length === 0 &&
    (Date.now() - new Date(currentThread.createdAt).getTime() < 2000);

  // Ignore stale messages if we're in switch window OR thread is newly created
  const shouldIgnoreStaleMessages = isInSwitchWindow || isNewlyCreatedThread;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentThread?.messages.length]);

  const allMessages = flattenSteps(messages);
  const liveMessages = allMessages.filter(m => {
    const content = m.output?.trim() || '';
    // Skip welcome/intro messages - we now show the magnifying glass intro instead
    if (isWelcomeMessage(content)) return false;
    if (m.type === 'user_message') return true;
    if (m.type === 'assistant_message' && content) return true;
    if (m.type === 'run' && content.length > 50) return true;
    if (content.length > 20) return true;
    return false;
  });

  const storedMessages = currentThread?.messages || [];

  // During thread switch, ignore stale Chainlit messages for empty state check
  // This is detected SYNCHRONOUSLY during render (didJustSwitch) AND persists for 200ms
  const effectiveLiveMessages = shouldIgnoreStaleMessages ? [] : liveMessages;
  const isEffectivelyEmpty = storedMessages.length === 0 && effectiveLiveMessages.length === 0 && !loading;

  if (isEffectivelyEmpty) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          {/* CVS Clinical Code Finder Logo */}
          <img
            src="/cvs clinical code finder.png"
            alt="CVS Clinical Code Finder"
            className="h-24 w-auto mx-auto mb-6"
          />
          <p className="text-[var(--text-secondary)] mb-6">
            Search across ICD-10, LOINC, RxTerms, HCPCS, UCUM, and HPO code systems.
          </p>
          <div className="text-sm text-[var(--text-muted)]">
            <p className="mb-2">Try searching for:</p>
            <ul className="space-y-1.5 text-[var(--text-secondary)]">
              <li><span className="text-[var(--accent-primary)]">"diabetes"</span> for diagnosis codes</li>
              <li><span className="text-[var(--accent-primary)]">"glucose test"</span> for lab codes</li>
              <li><span className="text-[var(--accent-primary)]">"metformin 500mg"</span> for medications</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // Show live messages only if we have them AND we're not ignoring stale data
  const hasLiveMessages = effectiveLiveMessages.length > 0 || (loading && !shouldIgnoreStaleMessages);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {hasLiveMessages ? (
          <>
            {liveMessages.map((message) => (
              <Message
                key={message.id}
                message={message}
                actions={actions?.filter((a) => a.forId === message.id) || []}
              />
            ))}
            {loading && <SkeletonLoading />}
          </>
        ) : (
          storedMessages.map((message) => (
            <HistoricalMessage key={message.id} message={message} />
          ))
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
