import { useState, useRef, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sparkles,
  Send,
  Copy,
  Check,
  Trash2,
  Bot,
  User,
  AlertTriangle,
} from "lucide-react";

import aiService from "@/services/aiService";

// ---------------------------------------------------------------------------
// Minimal markdown renderer (bold, italic, inline code, code blocks, links,
// lists, headings). Kept dependency-free since no markdown library was
// listed among the existing architecture.
// ---------------------------------------------------------------------------
function renderInline(text, keyPrefix) {
  const parts = [];
  const regex = /(\*\*.+?\*\*|\*.+?\*|`.+?`|\[.+?\]\(.+?\))/g;
  let lastIndex = 0;
  let match;
  let idx = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-${idx++}`;

    if (token.startsWith("**")) {
      parts.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      parts.push(
        <code
          key={key}
          className="rounded bg-black/10 px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("[")) {
      const linkMatch = token.match(/\[(.+?)\]\((.+?)\)/);
      parts.push(
        <a
          key={key}
          href={linkMatch[2]}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2"
        >
          {linkMatch[1]}
        </a>
      );
    } else if (token.startsWith("*")) {
      parts.push(<em key={key}>{token.slice(1, -1)}</em>);
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function Markdown({ text }) {
  if (!text) return null;

  const lines = text.split("\n");
  const blocks = [];
  let listBuffer = [];
  let codeBuffer = null;

  const flushList = (key) => {
    if (listBuffer.length) {
      blocks.push(
        <ul key={key} className="list-disc space-y-1 pl-5">
          {listBuffer.map((item, i) => (
            <li key={i}>{renderInline(item, `li-${key}-${i}`)}</li>
          ))}
        </ul>
      );
      listBuffer = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.trim().startsWith("```")) {
      if (codeBuffer === null) {
        codeBuffer = [];
      } else {
        blocks.push(
          <pre
            key={`code-${i}`}
            className="overflow-x-auto rounded-md bg-black/85 p-3 text-xs text-white"
          >
            <code>{codeBuffer.join("\n")}</code>
          </pre>
        );
        codeBuffer = null;
      }
      return;
    }

    if (codeBuffer !== null) {
      codeBuffer.push(line);
      return;
    }

    if (/^[-*]\s+/.test(line.trim())) {
      listBuffer.push(line.trim().replace(/^[-*]\s+/, ""));
      return;
    }
    flushList(`flush-${i}`);

    if (/^#{1,3}\s+/.test(line.trim())) {
      const level = line.trim().match(/^#+/)[0].length;
      const content = line.trim().replace(/^#{1,3}\s+/, "");
      const Tag = level === 1 ? "h3" : level === 2 ? "h4" : "h5";
      blocks.push(
        <Tag key={`h-${i}`} className="font-semibold">
          {renderInline(content, `h-${i}`)}
        </Tag>
      );
      return;
    }

    if (line.trim() === "") {
      return;
    }

    blocks.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {renderInline(line, `p-${i}`)}
      </p>
    );
  });

  flushList("flush-end");

  return <div className="flex flex-col gap-2">{blocks}</div>;
}

const SUGGESTED_PROMPTS = [
  {
    label: "🏙️ Estate Overview",
    prompt: "Give me an overview of the estate.",
  },
  {
    label: "🚨 Open Complaints",
    prompt: "Show unresolved complaints.",
  },
  {
    label: "🛠️ Pending Maintenance",
    prompt: "Show pending maintenance tasks.",
  },
  {
    label: "🎯 Today's Priorities",
    prompt: "Based on current estate data, what should I focus on today?",
  },
];

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-2">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable, ignore
    }
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-6 w-6"
      onClick={handleCopy}
      aria-label="Copy response"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </Button>
  );
}

export default function Chat() {

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (overrideText) => {
    const messageText = (overrideText ?? input).trim();
    if (!messageText || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: messageText }]);
    setInput("");
    setLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      // Existing endpoint preserved: POST ai/ via aiService.askAI({ question })
      const res = await aiService.askAIV3({ 
        question: messageText 
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: res?.response,
          data: res?.data,
          cypher: res?.cypher,
        },
      ]);
    } catch (err) {
      console.error(err);

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: err.response?.data?.error || "Error connecting to AI",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const clearChat = () => setMessages([]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          <h1 className="text-base font-semibold">Assistant</h1>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="gap-2"
          onClick={clearChat}
          disabled={!hasMessages}
        >
          <Trash2 className="h-4 w-4" />
          <span className="hidden sm:inline">Clear chat</span>
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
          {!hasMessages && (
            <div className="flex flex-col items-center gap-6 py-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Estate AI Assistant</h2>
                <p className="text-sm text-muted-foreground">
                  Ask questions about complaints, residents, properties,
                  maintenance, and estate insights.
                </p>
              </div>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTED_PROMPTS.map(({ label, prompt }) => (
                  <Card
                    key={label}
                    className="cursor-pointer transition-colors hover:bg-muted"
                    onClick={() => send(prompt)}
                  >
                    <CardContent className="p-3 text-left text-sm">
                      {label}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => {
            const isUser = m.role === "user";
            return (
              <div
                key={i}
                className={`flex items-start gap-3 ${
                  isUser ? "flex-row-reverse" : ""
                }`}
              >
                <div
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                    isUser ? "bg-primary text-primary-foreground" : "bg-muted"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div
                  className={`group relative max-w-[80%] rounded-2xl px-4 py-2.5 text-sm sm:max-w-[70%] ${
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : m.isError
                      ? "bg-destructive/10 text-destructive"
                      : "bg-muted"
                  }`}
                >
                  {m.isError && (
                    <div className="mb-1 flex items-center gap-1.5 text-xs font-medium">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Something went wrong
                    </div>
                  )}

                  {isUser ? (
                    <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>
                  ) : (
                    <Markdown text={m.text} />
                  )}

                  {m.data !== undefined && (
                    <pre className="mt-2 overflow-x-auto rounded-md bg-black/85 p-2 text-xs text-white">
                      {JSON.stringify(m.data, null, 2)}
                    </pre>
                  )}

                  {!isUser && !m.isError && m.text && (
                    <div className="mt-1 flex justify-end opacity-0 transition-opacity group-hover:opacity-100">
                      <CopyButton text={m.text} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl bg-muted px-4 py-1">
                <TypingIndicator />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Composer */}
      <div className="border-t px-4 py-3 sm:px-6">
        <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about complaints, residents, properties, or maintenance..."
            rows={1}
            className="max-h-40 flex-1 resize-none"
          />
          <Button
            type="button"
            size="icon"
            onClick={() => send()}
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mx-auto mt-2 w-full max-w-3xl text-center text-xs text-muted-foreground">
          Press Enter to send, Shift+Enter for a new line.
        </p>
      </div>
    </div>
  );
}