// ABOUTME: Single chat message component with clean card-based layout.
// ABOUTME: Displays messages with structured code results and action buttons.

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChevronDown, ChevronRight, Stethoscope, Pill, FlaskConical, ClipboardList, Ruler, Dna } from 'lucide-react';
import { useChatData } from '@chainlit/react-client';
import { ActionButton } from './ActionButton';
import { CodeResultCard, parseCodeResults, hasCodeResults } from './CodeResultCard';
import type { IAction, IStep } from '@chainlit/react-client';

const SYSTEM_ICONS: Record<string, typeof Stethoscope> = {
  'ICD-10-CM': Stethoscope,
  'RxTerms': Pill,
  'LOINC': FlaskConical,
  'HCPCS': ClipboardList,
  'UCUM': Ruler,
  'HPO': Dna,
};

interface MessageProps {
  message: IStep;
  actions: IAction[];
}

function isThinkingBlock(content: string): boolean {
  return content.startsWith('Found') && content.includes('How we found these:');
}

function extractResultCount(content: string): string | null {
  const match = content.match(/^Found (\d+) results?/);
  return match ? match[0] : null;
}


export function Message({ message, actions }: MessageProps) {
  const [showThinking, setShowThinking] = useState(false);
  const { chatSettingsValue } = useChatData();
  const showHierarchy = chatSettingsValue?.show_hierarchy ?? true;
  const isUser = message.type === 'user_message' || message.name === 'User';
  const content = message.output || '';
  const isThinking = !isUser && isThinkingBlock(content);

  const formatTime = (createdAt: number | string) => {
    const date = typeof createdAt === 'number'
      ? new Date(createdAt)
      : new Date(createdAt);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const containsResults = !isUser && hasCodeResults(content);
  const parsedResults = containsResults ? parseCodeResults(content) : null;

  const filteredActions = actions.filter(a => {
    if (a.name === 'add_to_bundle') return false;
    if (a.name === 'export_csv') return false;
    if (a.name === 'followup') {
      const payload = a.payload as { type?: string } | undefined;
      if (payload?.type === 'check_billable') return false;
    }
    return true;
  });

  return (
    <div className={`${isUser ? 'flex justify-end' : ''}`}>
      {isUser ? (
        // User message - right-aligned, subtle styling
        <div className="max-w-[70%]">
          <div className="px-4 py-2.5 bg-[var(--accent-soft)] text-[var(--text-primary)] rounded-2xl rounded-br-sm">
            <p className="text-sm leading-relaxed">{content}</p>
          </div>
          {message.createdAt && (
            <p className="text-xs text-[var(--text-muted)] mt-1 text-right">
              {formatTime(message.createdAt)}
            </p>
          )}
        </div>
      ) : containsResults && parsedResults ? (
        // Assistant message with code results - always expanded
        <div className="space-y-4">
          {/* Summary */}
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
                      p: ({ children }) => <p className="text-sm leading-relaxed mb-2">{children}</p>,
                      code: ({ children, ...props }) => {
                        const codeText = String(children).trim();
                        const isClinicalCode = /^[A-Z0-9][A-Z0-9.:-]*[0-9]$/i.test(codeText);
                        return (
                          <code
                            className={`px-1.5 py-0.5 rounded font-mono text-xs font-semibold ${
                              isClinicalCode
                                ? 'bg-[rgba(204,0,0,0.15)] text-[#e53e3e] border border-[rgba(204,0,0,0.3)] dark:bg-[rgba(255,107,107,0.15)] dark:text-[#ff6b6b] dark:border-[rgba(255,107,107,0.3)]'
                                : 'bg-[var(--accent-softer)] text-[var(--accent-primary)]'
                            }`}
                            {...props}
                          >
                            {children}
                          </code>
                        );
                      },
                      strong: ({ children }) => (
                        <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>
                      ),
                      h3: ({ children }) => (
                        <h3 className="text-sm font-semibold text-[var(--accent-primary)] mt-3 mb-2 pb-1 border-b border-[var(--border-subtle)]">
                          {children}
                        </h3>
                      ),
                      li: ({ children }) => (
                        <li className="text-sm leading-relaxed mb-1.5 ml-4">{children}</li>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc list-outside mb-2">{children}</ul>
                      ),
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

          {/* Results by system - always visible */}
          {Array.from(parsedResults.systems.entries()).map(([system, results]) => {
            const SystemIcon = SYSTEM_ICONS[system] || ClipboardList;
            return (
              <div
                key={system}
                className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-xl overflow-hidden shadow-theme-sm transition-theme"
              >
                {/* System header */}
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

                {/* Results list */}
                <div className="divide-y divide-[var(--border-subtle)]">
                  {results.map((result, idx) => (
                    <CodeResultCard key={`${result.code}-${idx}`} result={result} showHierarchy={showHierarchy} />
                  ))}
                </div>
              </div>
            );
          })}

          {/* Timestamp */}
          {message.createdAt && (
            <p className="text-xs text-[var(--text-muted)]">
              {formatTime(message.createdAt)}
            </p>
          )}
        </div>
      ) : isThinking ? (
        // Thinking block - collapsible, subtle
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
        // Regular assistant message - clean card
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
                    const codeText = String(children).trim();
                    // Check if this looks like a clinical code (alphanumeric with dots/dashes)
                    const isClinicalCode = /^[A-Z0-9][A-Z0-9.-]*[0-9]$/i.test(codeText);

                    return isInline ? (
                      <code
                        className={`px-1.5 py-0.5 rounded font-mono text-xs font-semibold ${
                          isClinicalCode
                            ? 'bg-[rgba(204,0,0,0.15)] text-[#e53e3e] border border-[rgba(204,0,0,0.3)] dark:bg-[rgba(255,107,107,0.15)] dark:text-[#ff6b6b] dark:border-[rgba(255,107,107,0.3)]'
                            : 'bg-[var(--accent-softer)] text-[var(--accent-primary)]'
                        }`}
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
                  strong: ({ children }) => (
                    <strong className="font-semibold text-[var(--text-primary)]">
                      {children}
                    </strong>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-semibold text-[var(--accent-primary)] mt-4 mb-2 pb-1 border-b border-[var(--border-subtle)]">
                      {children}
                    </h3>
                  ),
                  li: ({ children }) => (
                    <li className="text-sm leading-relaxed mb-1.5">
                      {children}
                    </li>
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>

          {/* Timestamp */}
          {message.createdAt && (
            <p className="text-xs text-[var(--text-muted)] mt-2">
              {formatTime(message.createdAt)}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      {filteredActions.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {filteredActions.map((action) => (
            <ActionButton key={action.id} action={action} />
          ))}
        </div>
      )}
    </div>
  );
}
