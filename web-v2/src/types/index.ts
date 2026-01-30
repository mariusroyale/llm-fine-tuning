// Query Intent types matching backend
export type QueryIntent =
  | 'definition'
  | 'explanation'
  | 'list_count'
  | 'usage'
  | 'search'
  | 'comparison'
  | 'schema';

// Source code chunk from RAG
export interface Source {
  file_path: string;
  start_line: number;
  end_line: number;
  class_name: string | null;
  method_name: string | null;
  chunk_type: string;
  language: string;
  content: string;
  score: number;
}

// Query analysis from backend
export interface QueryAnalysis {
  intent: QueryIntent;
  class_names: string[];
  primary_terms: string[];
}

// WebSocket message types
export type WSMessageType = 'status' | 'analysis' | 'sources' | 'answer' | 'done' | 'error';

export interface WSMessage {
  type: WSMessageType;
  content: unknown;
}

export interface WSStatusMessage extends WSMessage {
  type: 'status';
  content: string;
}

export interface WSAnalysisMessage extends WSMessage {
  type: 'analysis';
  content: QueryAnalysis;
}

export interface WSSourcesMessage extends WSMessage {
  type: 'sources';
  content: Source[];
}

export interface WSAnswerMessage extends WSMessage {
  type: 'answer';
  content: string;
}

export interface WSDoneMessage extends WSMessage {
  type: 'done';
  content: {
    model: string;
    num_sources: number;
  };
}

export interface WSErrorMessage extends WSMessage {
  type: 'error';
  content: string;
}

// Chat message in UI
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
  analysis?: QueryAnalysis;
  isLoading?: boolean;
  error?: string;
}

// Query request to backend
export interface QueryRequest {
  question: string;
  language?: string | null;
  use_hybrid_search?: boolean;
  top_k?: number | null;
}

// Settings
export interface Settings {
  language: string;
  hybridSearch: boolean;
  showSources: boolean;
}
