// ABOUTME: Hook that syncs Chainlit messages to the chat history store.
// ABOUTME: Auto-creates threads and names them from the first user message.

import { useEffect, useRef, useCallback } from 'react';
import { useChatMessages } from '@chainlit/react-client';
import type { IStep } from '@chainlit/react-client';
import { useChatHistoryStore } from '../stores/chatHistoryStore';

// Check if message is the welcome/intro message (should not be stored)
function isWelcomeMessage(content: string): boolean {
  return content.includes('What clinical code are you looking for?') ||
         (content.includes('Search across') && content.includes('ICD-10-CM'));
}

// Recursively flatten all steps (matches MessageList's flattenSteps)
function flattenAllSteps(steps: IStep[]): IStep[] {
  const result: IStep[] = [];
  for (const step of steps) {
    if (step.output && step.output.trim()) {
      result.push(step);
    }
    if (step.steps && step.steps.length > 0) {
      result.push(...flattenAllSteps(step.steps));
    }
  }
  return result;
}

export function useChatHistorySync() {
  const { messages } = useChatMessages();
  const {
    threads,
    liveThreadId,
    createThread,
    addMessage,
  } = useChatHistoryStore();

  // Track ALL processed message IDs globally - NEVER reset on thread switch
  const processedIds = useRef<Set<string>>(new Set());
  // Map each message ID to the thread it was ORIGINALLY synced to
  const messageThreadMap = useRef<Map<string, string>>(new Map());
  // Flag to pause syncing during thread switch
  const isSwitching = useRef(false);
  // Track the previous liveThreadId to detect switches
  const prevThreadId = useRef<string | null>(null);

  useEffect(() => {
    // Detect thread switch and pause syncing briefly
    if (prevThreadId.current !== null && prevThreadId.current !== liveThreadId) {
      isSwitching.current = true;
      // Resume syncing after a brief delay to let Recoil state settle
      const timer = setTimeout(() => {
        isSwitching.current = false;
      }, 100);
      prevThreadId.current = liveThreadId;
      return () => clearTimeout(timer);
    }
    prevThreadId.current = liveThreadId;

    // Don't sync while switching threads
    if (isSwitching.current) return;

    // If no live thread exists, create one
    if (!liveThreadId && threads.length === 0) {
      createThread();
      return;
    }
    if (!liveThreadId) return;

    // Flatten all messages recursively (same as display logic)
    const allSteps = flattenAllSteps(messages);

    // Process each step
    for (const step of allSteps) {
      // Skip if already processed
      if (processedIds.current.has(step.id)) continue;

      // Check if this message was already assigned to a different thread
      const assignedThread = messageThreadMap.current.get(step.id);
      if (assignedThread && assignedThread !== liveThreadId) {
        continue;
      }

      const content = step.output?.trim() || '';

      // User messages
      if (step.type === 'user_message' && content) {
        processedIds.current.add(step.id);
        messageThreadMap.current.set(step.id, liveThreadId);
        addMessage(liveThreadId, {
          role: 'user',
          content: content,
        });
        continue;
      }

      // Skip welcome messages
      if (isWelcomeMessage(content)) {
        processedIds.current.add(step.id);
        continue;
      }

      // Assistant messages - be generous with what we sync
      // Lower threshold to 20 chars to match display filtering
      if (content.length > 20) {
        processedIds.current.add(step.id);
        messageThreadMap.current.set(step.id, liveThreadId);
        addMessage(liveThreadId, {
          role: 'assistant',
          content: content,
        });
      }
    }
  }, [messages, liveThreadId, threads.length, createThread, addMessage]);

  // Reset tracking ONLY for new chat sessions (not thread switches)
  const resetTracking = useCallback(() => {
    processedIds.current = new Set();
    messageThreadMap.current = new Map();
    isSwitching.current = false;
    prevThreadId.current = null;
  }, []);

  // Pause syncing during thread switch (call this before selectThread)
  const pauseSync = useCallback(() => {
    isSwitching.current = true;
  }, []);

  return { resetTracking, pauseSync };
}
