import { useEffect, useRef, useState } from "react";
import { Sidebar, ChatInput, Message, SourcesPanel } from "./components";
import { useChat } from "./hooks";
import type { Source } from "./types";

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-glow">
          <svg
            className="w-8 h-8 text-white"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            <polyline points="7.5 4.21 12 6.81 16.5 4.21" />
            <polyline points="7.5 19.79 7.5 14.6 3 12" />
            <polyline points="21 12 16.5 14.6 16.5 19.79" />
            <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
            <line x1="12" y1="22.08" x2="12" y2="12" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Welcome to Koda
        </h2>
        <p className="text-gray-400 mb-8 leading-relaxed">
          Your intelligent codebase assistant. Ask questions about your code,
          explore patterns, and understand your architecture.
        </p>
        <div className="grid grid-cols-2 gap-3 text-left">
          {[
            { q: "What does UserService do?", label: "Classes" },
            { q: "How does authentication work?", label: "Flow" },
            { q: "List all entity classes", label: "Discovery" },
            { q: "Where is PaymentProcessor used?", label: "Usage" },
          ].map(({ q, label }) => (
            <div
              key={q}
              className="group p-3 rounded-xl bg-gray-900/50 border border-gray-800 hover:border-accent/30 hover:bg-accent/5 cursor-pointer transition-all"
            >
              <span className="text-2xs font-medium text-accent uppercase tracking-wider">
                {label}
              </span>
              <p className="text-sm text-gray-300 mt-1 group-hover:text-white transition-colors">
                {q}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function App() {
  const {
    messages,
    isConnected,
    isLoading,
    sendQuestion,
    clearMessages,
    settings,
    updateSettings,
    stats,
  } = useChat();

  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [currentSources, setCurrentSources] = useState<Source[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleViewSources = (sources: Source[]) => {
    setCurrentSources(sources);
    setSourcesOpen(true);
  };

  const hasConversation = messages.length > 1; // More than welcome message

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-950">
      {/* Sidebar */}
      <Sidebar
        settings={settings}
        onSettingsChange={updateSettings}
        onClearChat={clearMessages}
        stats={stats}
        isConnected={isConnected}
      />

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-radial from-accent/5 via-transparent to-transparent pointer-events-none" />

        {/* Chat area */}
        {!hasConversation ? (
          <EmptyState />
        ) : (
          <div className="flex-1 overflow-y-auto relative">
            <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
              {messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  showSources={settings.showSources}
                  onViewSources={handleViewSources}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={sendQuestion}
          disabled={isLoading}
          isConnected={isConnected}
        />
      </main>

      {/* Sources Panel */}
      <SourcesPanel
        sources={currentSources}
        isOpen={sourcesOpen}
        onClose={() => setSourcesOpen(false)}
      />
    </div>
  );
}

export default App;
