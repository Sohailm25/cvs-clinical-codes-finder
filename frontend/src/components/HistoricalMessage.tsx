// ABOUTME: Displays a message from stored chat history.
// ABOUTME: Read-only view of past conversations with user/assistant styling.

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChevronDown, ChevronRight, Stethoscope, Pill, FlaskConical, ClipboardList, Ruler, Dna } from 'lucide-react';
import { useChatData } from '@chainlit/react-client';
import type { ChatMessage } from '../stores/chatHistoryStore';
import { CodeResultCard, parseCodeResults, hasCodeResults } from './CodeResultCard';

const SYSTEM_ICONS: Record<string, typeof Stethoscope> = {
  'ICD-10-CM': Stethoscope,
  'RxTerms': Pill,
  'LOINC': FlaskConical,
  'HCPCS': ClipboardList,
  'UCUM': Ruler,
  'HPO': Dna,
};

interface HistoricalMessageProps {
  message: ChatMessage;
}

function isThinkingBlock(content: string): boolean {
  return content.startsWith('Found') && content.includes('How we found these:');
}

function extractResultCount(content: string): string | null {
  const match = content.match(/^Found (\d+) results?/);
  return match ? match[0] : null;
}

export function HistoricalMessage({ message }: HistoricalMessageProps) {
  const [showThinking, setShowThinking] = useState(false);
  const { chatSettingsValue } = useChatData();
  const showHierarchy = chatSettingsValue?.show_hierarchy ?? true;
  const isUser = message.role === 'user';
  const content = message.content;

  const isThinking = !isUser && isThinkingBlock(content);
  const containsResults = !isUser && !isThinking && hasCodeResults(content);
  const parsedResults = containsResults ? parseCodeResults(content) : null;

  return (
    <div className={`${isUser ? 'flex justify-end' : ''}`}>
      {isUser ? (
        <div className="max-w-[70%]">
          <div className="px-4 py-2.5 bg-[var(--accent-soft)] text-[var(--text-primary)] rounded-2xl rounded-br-sm">
            <p className="text-sm leading-relaxed">{content}</p>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1 text-right">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      ) : containsResults && parsedResults ? (
        <div className="space-y-4">
          {parsedResults.summary && (() => {
            // Split summary from multi-hop expansion for separate styling
            const multiHopMatch = parsedResults.summary.match(/\*{0,2}🔗?\s*Multi-hop expansion\*{0,2}:\s*(.+?)$/i);
            const mainSummary = parsedResults.summary.replace(/\s*\*{0,2}🔗?\s*Multi-hop expansion\*{0,2}:\s*.+$/i, '').trim();
            const multiHopText = multiHopMatch ? multiHopMatch[1].trim() : null;

            return (
              <div className="text-[var(--text-primary)]">
                {mainSummary && (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="text-sm leading-relaxed">{children}</p>,
                    }}
                  >
                    {mainSummary}
                  </ReactMarkdown>
                )}
                {multiHopText && (
                  <p className="text-sm leading-relaxed mt-3 text-[var(--text-secondary)]">
                    <span className="font-semibold text-[var(--text-primary)]">Multi-hop expansion:</span> {multiHopText}
                  </p>
                )}
              </div>
            );
          })()}

          {Array.from(parsedResults.systems.entries()).map(([system, results]) => {
            const SystemIcon = SYSTEM_ICONS[system] || ClipboardList;
            return (
              <div
                key={system}
                className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-xl overflow-hidden shadow-theme-sm transition-theme"
              >
                <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <SystemIcon className="w-4 h-4 text-[var(--accent-primary)]" />
                      <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                        {system}
                      </h3>
                    </div>
                    <span className="text-xs text-[var(--text-muted)] bg-[var(--accent-softer)] px-2 py-0.5 rounded-full">
                      {results.length} result{results.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>

                <div className="divide-y divide-[var(--border-subtle)]">
                  {results.map((result, idx) => (
                    <CodeResultCard key={`${result.code}-${idx}`} result={result} showHierarchy={showHierarchy} />
                  ))}
                </div>
              </div>
            );
          })}

          <p className="text-xs text-[var(--text-muted)]">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      ) : isThinking ? (
        // Thinking block - collapsible dropdown
        <div className="inline-block rounded-lg border border-[var(--border-default)] bg-[var(--bg-secondary)] overflow-hidden transition-theme">
          <button
            onClick={() => setShowThinking(!showThinking)}
            className="flex items-center gap-2 px-3 py-2 text-xs hover:bg-[var(--accent-softer)] w-full transition-colors"
          >
            {showThinking ? (
              <ChevronDown className="w-3 h-3 text-[var(--text-muted)]" />
            ) : (
              <ChevronRight className="w-3 h-3 text-[var(--text-muted)]" />
            )}
            <span className="text-[var(--text-secondary)]">
              {extractResultCount(content) || 'Processing details'}
            </span>
            <span className="text-[var(--text-muted)]">
              {showThinking ? 'Hide' : 'Show'} details
            </span>
          </button>
          {showThinking && (
            <div className="px-3 py-2 text-xs text-[var(--text-muted)] border-t border-[var(--border-subtle)] max-h-40 overflow-y-auto">
              <pre className="whitespace-pre-wrap font-mono">{content}</pre>
            </div>
          )}
        </div>
      ) : (
        <div className="max-w-[85%]">
          <div className="text-[var(--text-primary)]">
            <div className="prose prose-sm max-w-none dark:prose-invert
              prose-p:text-[var(--text-primary)] prose-p:leading-relaxed
              prose-code:text-[var(--accent-primary)] prose-code:bg-[var(--accent-softer)]
              prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-xs
              prose-a:text-[var(--accent-primary)] prose-a:no-underline hover:prose-a:underline"
            >
              <ReactMarkdown
                components={{
                  code: ({ className, children, ...props }) => {
                    const isInline = !className;
                    return isInline ? (
                      <code
                        className="px-1.5 py-0.5 bg-[var(--accent-softer)] text-[var(--accent-primary)] rounded font-mono text-xs"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  a: ({ children, ...props }) => (
                    <a className="text-[var(--accent-primary)] hover:underline" {...props}>
                      {children}
                    </a>
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>

          <p className="text-xs text-[var(--text-muted)] mt-2">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      )}
    </div>
  );
}
