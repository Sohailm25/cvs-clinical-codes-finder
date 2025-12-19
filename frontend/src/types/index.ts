// ABOUTME: TypeScript type definitions for the Clinical Codes Finder frontend.
// ABOUTME: Defines interfaces for bundle items, code results, and chat messages.

export interface BundleItem {
  system: string;
  code: string;
  display: string;
}

export interface CodeResult {
  system: string;
  code: string;
  display: string;
  confidence: number;
  metadata?: Record<string, unknown>;
  source?: Record<string, unknown>;
}

export interface ChatSettings {
  clarification_enabled: boolean;
  multi_hop_enabled: boolean;
  show_hierarchy: boolean;
}

export interface ActionPayload {
  type?: string;
  system?: string;
  code?: string;
  display?: string;
  query?: string;
  [key: string]: unknown;
}
