import { Box, User, FileCode, Copy, Check, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useState } from "react";
import type { ChatMessage, Source } from "../types";

interface MessageProps {
  message: ChatMessage;
  showSources: boolean;
  statusMessage?: string | null;
  onViewSources?: (sources: Source[]) => void;
}

function ThinkingIndicator({ statusMessage }: { statusMessage?: string | null }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex gap-1">
        <span className="thinking-dot" />
        <span className="thinking-dot" />
        <span className="thinking-dot" />
      </div>
      <span className="text-sm text-gray-500">
        {statusMessage || "Thinking..."}
      </span>
    </div>
  );
}

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="btn-icon w-7 h-7 opacity-0 group-hover:opacity-100 transition-opacity"
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-success" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

function IntentBadge({ intent }: { intent: string }) {
  return (
    <span className="badge-accent">
      <Sparkles className="w-3 h-3" />
      {intent.replace("_", " ")}
    </span>
  );
}

function ClassBadge({ name }: { name: string }) {
  return <span className="badge-muted">{name}</span>;
}

export function Message({ message, showSources, statusMessage, onViewSources }: MessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-4 animate-slide-up ${isUser ? "flex-row-reverse" : ""}`}
    >
      {/* Avatar */}
      <div
        className={`
        flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
        ${
          isUser
            ? "bg-gradient-to-br from-accent to-purple-600"
            : "bg-gray-800 border border-gray-700"
        }
      `}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Box className="w-4 h-4 text-accent" />
        )}
      </div>

      {/* Content */}
      <div
        className={`flex flex-col gap-2 max-w-[85%] min-w-0 ${isUser ? "items-end" : "items-start"}`}
      >
        {/* Sender name */}
        <span className="text-2xs font-medium text-gray-500 uppercase tracking-wider">
          {isUser ? "You" : "Koda"}
        </span>

        {/* Analysis badges */}
        {!isUser && message.analysis && (
          <div className="flex flex-wrap gap-1.5">
            <IntentBadge intent={message.analysis.intent} />
            {message.analysis.class_names.slice(0, 3).map((name) => (
              <ClassBadge key={name} name={name} />
            ))}
          </div>
        )}

        {/* Message bubble */}
        {message.isLoading ? (
          <div className="card">
            <ThinkingIndicator statusMessage={statusMessage} />
          </div>
        ) : message.error ? (
          <div className="card border-error/30 bg-error/5">
            <div className="px-4 py-3 text-sm text-error">{message.error}</div>
          </div>
        ) : (
          <div
            className={`
            rounded-2xl overflow-hidden
            ${
              isUser
                ? "bg-gradient-to-br from-accent to-purple-600 text-white px-4 py-3 rounded-tr-md"
                : "card px-4 py-3 rounded-tl-md"
            }
          `}
          >
            {isUser ? (
              <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                {message.content}
              </p>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || "");
                      const code = String(children).replace(/\n$/, "");
                      const isInline = !match && !code.includes("\n");

                      if (isInline) {
                        return (
                          <code
                            className="px-1.5 py-0.5 bg-gray-800 text-accent-hover rounded text-[13px] font-mono"
                            {...props}
                          >
                            {children}
                          </code>
                        );
                      }

                      const language = match ? match[1] : "text";

                      return (
                        <div className="relative group my-4 -mx-4 sm:mx-0 rounded-lg overflow-hidden border border-gray-800">
                          <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800">
                            <span className="text-2xs font-medium text-gray-500 uppercase tracking-wider">
                              {language}
                            </span>
                            <CopyButton code={code} />
                          </div>
                          <SyntaxHighlighter
                            style={oneDark}
                            language={language}
                            PreTag="div"
                            customStyle={{
                              margin: 0,
                              borderRadius: 0,
                              background: "#0c0c0e",
                              fontSize: "13px",
                            }}
                          >
                            {code}
                          </SyntaxHighlighter>
                        </div>
                      );
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {/* Sources button */}
        {!isUser &&
          showSources &&
          message.sources &&
          message.sources.length > 0 && (
            <button
              onClick={() => onViewSources?.(message.sources!)}
              className="group flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs
                       bg-gray-900/50 border border-gray-800 text-gray-400
                       hover:border-accent/30 hover:text-accent hover:bg-accent/5
                       transition-all duration-200"
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>
                {message.sources.length} source
                {message.sources.length > 1 ? "s" : ""}
              </span>
              <span className="text-gray-600 group-hover:text-accent/60">
                →
              </span>
            </button>
          )}
      </div>
    </div>
  );
}
