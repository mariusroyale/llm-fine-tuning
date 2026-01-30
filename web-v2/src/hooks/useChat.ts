import { useCallback, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import type {
  ChatMessage,
  QueryAnalysis,
  Settings,
  Source,
  WSMessage,
} from '../types';

interface UseChatReturn {
  messages: ChatMessage[];
  isConnected: boolean;
  isLoading: boolean;
  statusMessage: string | null;
  sendQuestion: (question: string) => void;
  clearMessages: () => void;
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
  stats: {
    questionsAsked: number;
    sourcesRetrieved: number;
  };
}

const generateId = () => Math.random().toString(36).substring(2, 15);

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: `Hello! I'm **Koda**, your codebase assistant. I can help you understand your code by answering questions about:

- **Classes & Methods** - "What does UserService do?"
- **Code Flow** - "How does authentication work?"
- **Architecture** - "List all the entity classes"
- **Usage** - "Where is PaymentProcessor used?"

Ask me anything about your codebase!`,
  timestamp: new Date(),
};

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);
  const [pendingSources, setPendingSources] = useState<Source[]>([]);
  const [pendingAnalysis, setPendingAnalysis] = useState<QueryAnalysis | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings>({
    language: '',
    hybridSearch: true,
    showSources: true,
  });
  const [stats, setStats] = useState({
    questionsAsked: 0,
    sourcesRetrieved: 0,
  });

  const handleMessage = useCallback((message: WSMessage) => {
    try {
      switch (message.type) {
        case 'status':
          // Update status message for progress display
          setStatusMessage(message.content as string);
          break;

        case 'analysis':
          setPendingAnalysis(message.content as QueryAnalysis);
          break;

        case 'sources':
          const sources = message.content as Source[];
          if (Array.isArray(sources)) {
            setPendingSources(sources);
            setStats(prev => ({
              ...prev,
              sourcesRetrieved: prev.sourcesRetrieved + sources.length,
            }));
          } else {
            console.warn('[WebSocket] Sources message content is not an array:', sources);
            setPendingSources([]);
          }
          break;

        case 'answer':
          setMessages(prev => prev.map(msg =>
            msg.id === currentMessageId
              ? {
                  ...msg,
                  content: message.content as string,
                  sources: pendingSources,
                  analysis: pendingAnalysis || undefined,
                  isLoading: false,
                }
              : msg
          ));
          setPendingSources([]);
          setPendingAnalysis(null);
          setStatusMessage(null);
          break;

        case 'done':
          setIsLoading(false);
          setCurrentMessageId(null);
          setStatusMessage(null);
          break;

        case 'error':
          setMessages(prev => prev.map(msg =>
            msg.id === currentMessageId
              ? {
                  ...msg,
                  content: '',
                  error: message.content as string,
                  isLoading: false,
                }
              : msg
          ));
          setIsLoading(false);
          setCurrentMessageId(null);
          setStatusMessage(null);
          break;

        default:
          // Ignore unknown message types (like "start")
          console.warn('[WebSocket] Unknown message type:', (message as any).type);
          break;
      }
    } catch (error) {
      console.error('[WebSocket] Error handling message:', error, message);
    }
  }, [currentMessageId, pendingSources, pendingAnalysis]);

  const { isConnected, sendMessage } = useWebSocket({
    onMessage: handleMessage,
  });

  const sendQuestion = useCallback((question: string) => {
    if (!question.trim() || isLoading || !isConnected) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    // Add placeholder assistant message
    const assistantMessageId = generateId();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setCurrentMessageId(assistantMessageId);
    setIsLoading(true);
    setStats(prev => ({ ...prev, questionsAsked: prev.questionsAsked + 1 }));

    // Send to server
    sendMessage({
      question,
      language: settings.language || null,
      use_hybrid_search: settings.hybridSearch,
    });
  }, [isLoading, isConnected, sendMessage, settings]);

  const clearMessages = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
  }, []);

  const updateSettings = useCallback((newSettings: Partial<Settings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  return {
    messages,
    isConnected,
    isLoading,
    statusMessage,
    sendQuestion,
    clearMessages,
    settings,
    updateSettings,
    stats,
  };
}
