import { type KeyboardEvent, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isConnected: boolean;
}

export function ChatInput({ onSend, disabled, isConnected }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }
  };

  const canSend = value.trim() && !disabled && isConnected;

  return (
    <div className="border-t border-gray-800/50 bg-gray-950/80 backdrop-blur-xl">
      <div className="max-w-3xl mx-auto p-4">
        <div
          className={`
          relative rounded-xl border bg-gray-900/80 backdrop-blur transition-all duration-200
          ${
            !isConnected
              ? "border-error/30"
              : value
                ? "border-accent/30 shadow-glow"
                : "border-gray-800 hover:border-gray-700"
          }
        `}
        >
          {/* Gradient accent line */}
          <div
            className={`
            absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent to-transparent
            transition-opacity duration-300
            ${value ? "opacity-100" : "opacity-0"}
          `}
          />

          <div className="flex items-end gap-2 p-2">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              placeholder={
                isConnected ? "Ask about your codebase..." : "Connecting..."
              }
              disabled={!isConnected}
              rows={1}
              className="flex-1 px-3 py-2.5 bg-transparent text-gray-100 placeholder-gray-600
                         resize-none focus:outline-none max-h-40 text-[15px] leading-relaxed"
            />
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`
                flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center
                transition-all duration-200
                ${
                  canSend
                    ? "bg-accent text-white hover:bg-accent-hover shadow-subtle hover:shadow-glow active:scale-95"
                    : "bg-gray-800 text-gray-600 cursor-not-allowed"
                }
              `}
            >
              {disabled ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-center gap-4 text-2xs text-gray-600">
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400 font-mono">
              ↵
            </kbd>
            send
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400 font-mono">
              ⇧↵
            </kbd>
            new line
          </span>
        </div>
      </div>
    </div>
  );
}
