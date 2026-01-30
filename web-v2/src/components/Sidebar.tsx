import {
  Box,
  Sparkles,
  Trash2,
  Zap,
  Database,
  MessageSquare,
} from "lucide-react";
import type { Settings } from "../types";

interface SidebarProps {
  settings: Settings;
  onSettingsChange: (settings: Partial<Settings>) => void;
  onClearChat: () => void;
  stats: {
    questionsAsked: number;
    sourcesRetrieved: number;
  };
  isConnected: boolean;
}

const LANGUAGES = [
  { value: "", label: "All Languages" },
  { value: "java", label: "Java" },
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "go", label: "Go" },
  { value: "rust", label: "Rust" },
];

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Zap;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800">
      <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
        <Icon className="w-4 h-4 text-accent" />
      </div>
      <div>
        <div className="text-lg font-semibold text-white">{value}</div>
        <div className="text-2xs text-gray-500 uppercase tracking-wider">
          {label}
        </div>
      </div>
    </div>
  );
}

export function Sidebar({
  settings,
  onSettingsChange,
  onClearChat,
  stats,
  isConnected,
}: SidebarProps) {
  return (
    <aside className="w-72 bg-gray-900/30 border-r border-gray-800/50 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-gray-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-glow">
            <Box className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Koda</h1>
            <p className="text-2xs text-gray-500 uppercase tracking-wider">
              Codebase Assistant
            </p>
          </div>
        </div>

        {/* Connection status */}
        <div className="mt-4 flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-success" : "bg-error animate-pulse"}`}
          />
          <span className="text-xs text-gray-500">
            {isConnected ? "Connected" : "Reconnecting..."}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5 space-y-6 overflow-y-auto">
        {/* Stats */}
        <div className="space-y-2">
          <StatCard
            icon={MessageSquare}
            label="Questions"
            value={stats.questionsAsked}
          />
          <StatCard
            icon={Database}
            label="Sources"
            value={stats.sourcesRetrieved}
          />
        </div>

        <div className="divider" />

        {/* Settings */}
        <div className="space-y-4">
          <h3 className="text-2xs font-semibold text-gray-500 uppercase tracking-wider">
            Settings
          </h3>

          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">
                Language Filter
              </label>
              <select
                value={settings.language}
                onChange={(e) => onSettingsChange({ language: e.target.value })}
                className="select"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>

            <label className="flex items-center gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800 cursor-pointer hover:border-gray-700 transition-colors group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={settings.hybridSearch}
                  onChange={(e) =>
                    onSettingsChange({ hybridSearch: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-700 rounded-full peer-checked:bg-accent transition-colors" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform peer-checked:translate-x-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-1.5 text-sm text-gray-200">
                  <Sparkles className="w-3.5 h-3.5 text-accent" />
                  Hybrid Search
                </div>
                <p className="text-2xs text-gray-500 mt-0.5">
                  Semantic + keyword matching
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800 cursor-pointer hover:border-gray-700 transition-colors">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={settings.showSources}
                  onChange={(e) =>
                    onSettingsChange({ showSources: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-700 rounded-full peer-checked:bg-accent transition-colors" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform peer-checked:translate-x-4" />
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-200">Show Sources</div>
                <p className="text-2xs text-gray-500 mt-0.5">
                  Display code references
                </p>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800/50">
        <button
          onClick={onClearChat}
          className="btn-ghost w-full justify-center text-gray-500 hover:text-error"
        >
          <Trash2 className="w-4 h-4" />
          Clear conversation
        </button>
      </div>
    </aside>
  );
}
