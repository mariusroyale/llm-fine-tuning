import { X, FileCode, Hash, GitBranch, Copy, Check } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useState } from "react";
import type { Source } from "../types";

interface SourcesPanelProps {
  sources: Source[];
  isOpen: boolean;
  onClose: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return "text-success bg-success/10 border-success/30";
  if (score >= 0.6) return "text-warning bg-warning/10 border-warning/30";
  return "text-gray-400 bg-gray-800 border-gray-700";
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button onClick={handleCopy} className="btn-icon w-7 h-7" title="Copy code">
      {copied ? (
        <Check className="w-3.5 h-3.5 text-success" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

function SourceCard({ source }: { source: Source }) {
  const scorePercent = Math.round(source.score * 100);
  const scoreClass = getScoreColor(source.score);
  const fileName = source.file_path.split("/").pop() || source.file_path;

  return (
    <div className="card overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-accent flex-shrink-0" />
              <span
                className="text-sm font-medium text-gray-200 truncate"
                title={source.file_path}
              >
                {fileName}
              </span>
            </div>
            <p
              className="text-2xs text-gray-500 mt-1 font-mono truncate"
              title={source.file_path}
            >
              {source.file_path}
            </p>
          </div>
          <div
            className={`flex-shrink-0 px-2 py-1 text-2xs font-semibold rounded-md border ${scoreClass}`}
          >
            {scorePercent}%
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap gap-3 mt-3">
          <div className="flex items-center gap-1.5 text-2xs text-gray-500">
            <Hash className="w-3 h-3" />
            <span>
              Lines {source.start_line}–{source.end_line}
            </span>
          </div>
          {source.class_name && (
            <div className="flex items-center gap-1.5 text-2xs text-gray-500">
              <GitBranch className="w-3 h-3" />
              <span>{source.class_name}</span>
            </div>
          )}
          {source.method_name && (
            <span className="badge-muted text-2xs">{source.method_name}</span>
          )}
        </div>
      </div>

      {/* Code */}
      <div className="relative group">
        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
          <CopyButton text={source.content} />
        </div>
        <div className="max-h-64 overflow-auto">
          <SyntaxHighlighter
            style={oneDark}
            language={source.language || "text"}
            showLineNumbers
            startingLineNumber={source.start_line}
            customStyle={{
              margin: 0,
              borderRadius: 0,
              background: "#0c0c0e",
              fontSize: "12px",
              padding: "12px 16px",
            }}
            lineNumberStyle={{
              minWidth: "3em",
              paddingRight: "1em",
              color: "#3f3f46",
              fontStyle: "normal",
            }}
          >
            {source.content}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  );
}

export function SourcesPanel({ sources, isOpen, onClose }: SourcesPanelProps) {
  return (
    <>
      {/* Backdrop */}
      <div
        className={`
          fixed inset-0 bg-gray-950/60 backdrop-blur-sm z-40
          transition-opacity duration-300
          ${isOpen ? "opacity-100" : "opacity-0 pointer-events-none"}
        `}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className={`
        fixed top-0 right-0 h-full w-[480px] max-w-full
        bg-gray-900/95 backdrop-blur-xl border-l border-gray-800
        z-50 transition-transform duration-300 ease-out
        ${isOpen ? "translate-x-0" : "translate-x-full"}
      `}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                <FileCode className="w-4 h-4 text-accent" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">Sources</h2>
                <p className="text-2xs text-gray-500">
                  {sources.length} code reference
                  {sources.length !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <button onClick={onClose} className="btn-icon">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {sources.map((source) => (
              <SourceCard
                key={`${source.file_path}-${source.start_line}`}
                source={source}
              />
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
