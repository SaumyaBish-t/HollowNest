"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Edit2, Check, AlertCircle, FolderOpen, Paperclip, X, FileText, Film, Image as ImageIcon, Volume2, VolumeX, Copy, PanelLeft } from "lucide-react";
import { HollowMark } from "@/components/HollowMark";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import ProviderSelector from "./ProviderSelector";
import VoiceButton from "@/components/VoiceButton";
import { useTextToSpeech } from "@/hooks/useTextToSpeech";
import { streamAgentRun, updateSessionTitle, getSession, uploadFiles } from "@/lib/api";
import type { Session, Message } from "@/lib/api";

interface ChatPanelProps {
  sessionId: string | null;
  provider: string;
  model: string;
  onProviderChange: (provider: string, model: string) => void;
  providersData: Record<string, { label: string; models: string[] }>;
  connectedTools: string[];
  workspacePath: string;
  onWorkspaceChange: (path: string) => void;
  onSessionCreated: (id: string) => void;
  onToolCall: (id: string, name: string, args: any) => void;
  onToolResult: (id: string, name: string, result: string) => void;
  onDone: () => void;
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

export default function ChatPanel({
  sessionId,
  provider,
  model,
  onProviderChange,
  providersData,
  connectedTools,
  workspacePath,
  onWorkspaceChange,
  onSessionCreated,
  onToolCall,
  onToolResult,
  onDone,
  onToggleSidebar,
  sidebarOpen,
}: ChatPanelProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const { speak, stop: stopSpeaking, speaking: isSpeaking } = useTextToSpeech();
  
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [tempTitle, setTempTitle] = useState("");

  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const hasDraft = input.trim().length > 0 || pendingFiles.length > 0;
  const canSend = hasDraft && !isStreaming && !isUploading;

  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Session id of a session we just created via streaming — used to skip the
  // refetch that would otherwise wipe the live-streamed messages.
  const justCreatedSessionRef = useRef<string | null>(null);

  // Load session history if sessionId changes
  useEffect(() => {
    // This sessionId change came from a stream we just started — the user and
    // assistant messages are already live in state. Skip the reset/refetch,
    // otherwise we'd overwrite them with the half-saved DB copy.
    if (sessionId && sessionId === justCreatedSessionRef.current) {
      justCreatedSessionRef.current = null;
      return;
    }

    setIsStreaming(false);
    setIsUploading(false);

    if (!sessionId) {
      setSession(null);
      setMessages([]);
      setIsLoadingSession(false);
      return;
    }

    // Guard against a slow fetch for a previous session overwriting a newer one
    let cancelled = false;
    setIsLoadingSession(true);
    getSession(sessionId)
      .then((s) => {
        if (cancelled) return;
        setSession(s);
        setMessages(s.messages || []);
        if (s.provider && s.model) {
          onProviderChange(s.provider, s.model);
        }
      })
      .catch((e) => {
        if (!cancelled) console.error("Error loading session", e);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSession(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Recover from interrupted streams/uploads that can leave the composer locked.
  useEffect(() => {
    if (isStreaming && messages.length === 0) {
      setIsStreaming(false);
    }
    if (isUploading && pendingFiles.length === 0) {
      setIsUploading(false);
    }
  }, [isStreaming, isUploading, messages.length, pendingFiles.length]);

  // Auto-scroll — scroll the container itself, NOT scrollIntoView
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isStreaming]);

  // Clear the per-message "speaking" indicator once speech finishes
  useEffect(() => {
    if (!isSpeaking) setSpeakingMsgId(null);
  }, [isSpeaking]);

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  };

  const handleTitleSave = async () => {
    if (session && tempTitle.trim()) {
      try {
        const updated = await updateSessionTitle(session.id, tempTitle.trim());
        setSession(updated);
      } catch (e) {
        console.error("Failed to update title", e);
      }
    }
    setIsEditingTitle(false);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      const validFiles = files.filter(f => {
        if (f.size > 10 * 1024 * 1024) {
          setErrorMsg(`File ${f.name} exceeds 10MB limit.`);
          return false;
        }
        return true;
      });
      setPendingFiles(prev => [...prev, ...validFiles]);
    }
  };

  const removePendingFile = (idx: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSend = async () => {
    if (!canSend) return;
    setErrorMsg("");

    let uploadedAttachments: any[] = [];
    if (pendingFiles.length > 0) {
      setIsUploading(true);
      try {
        const res = await uploadFiles(pendingFiles);
        uploadedAttachments = res.files;
      } catch (e: any) {
        setErrorMsg("Failed to upload files: " + e.message);
        setIsUploading(false);
        return;
      }
      setIsUploading(false);
    }

    const userMsg: Message = {
      id: `local_user_${Date.now()}`,
      role: "user",
      content: input,
      created_at: new Date().toISOString(),
      tool_calls: [],
      attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
    };

    const assistantMsg: Message = {
      id: `local_ast_${Date.now()}`,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      tool_calls: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    setInput("");
    setPendingFiles([]);
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    try {
      const generator = streamAgentRun({
        message: userMsg.content || "",
        session_id: sessionId || undefined,
        provider,
        model,
        enabled_tools: connectedTools,
        workspace_path: workspacePath || undefined,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
      });

      for await (const event of generator) {
        if (event.type === "session_id") {
          if (!sessionId) {
            justCreatedSessionRef.current = event.session_id;
            onSessionCreated(event.session_id);
          }
        } else if (event.type === "text") {
          setMessages((prev) => {
            const copy = [...prev];
            const last = { ...copy[copy.length - 1] };
            last.content += event.content;
            copy[copy.length - 1] = last;
            return copy;
          });
        } else if (event.type === "tool_start") {
          const tcId = `tc_${Date.now()}_${Math.random()}`; // fake ID for tracking
          onToolCall(tcId, event.name, event.args);
        } else if (event.type === "tool_result") {
          // Just forward event, the panel will handle mapping
          onToolResult("any", event.name, event.result);
        } else if (event.type === "error") {
          setErrorMsg(event.message);
        }
      }
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to connect to backend");
    } finally {
      setIsStreaming(false);
      onDone();
    }
  };

  // Read a single message aloud — toggles off if it is already speaking.
  const handleSpeak = (msg: Message) => {
    if (speakingMsgId === msg.id) {
      stopSpeaking();
      setSpeakingMsgId(null);
    } else if (msg.content) {
      speak(msg.content);
      setSpeakingMsgId(msg.id);
    }
  };

  // Copy a message's full text to the clipboard.
  const handleCopy = async (msg: Message) => {
    if (!msg.content) return;
    try {
      await navigator.clipboard.writeText(msg.content);
      setCopiedMsgId(msg.id);
      setTimeout(
        () => setCopiedMsgId((id) => (id === msg.id ? null : id)),
        1800
      );
    } catch (e) {
      console.error("Copy failed", e);
    }
  };

  const EXAMPLES = [
    "List files in the workspace",
    "Write a Python function to parse JSON",
    "Debug why my React component isn't rendering",
  ];

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden min-w-0 min-h-0">
      {/* Top Bar */}
      <header className="h-[60px] shrink-0 border-b border-border bg-surface flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            title="Show / hide sidebar"
            className="t-all flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/[0.06] shrink-0"
          >
            <PanelLeft size={18} />
          </button>
          {!sidebarOpen && (
            <span
              className="wordmark shrink-0"
              style={{ fontSize: "1.4rem", letterSpacing: "2.5px" }}
            >
              HollowNest
            </span>
          )}
          {isEditingTitle ? (
            <div className="flex items-center gap-2">
              <Input
                value={tempTitle}
                onChange={(e) => setTempTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTitleSave()}
                className="h-8 max-w-[200px]"
                autoFocus
                onBlur={handleTitleSave}
              />
              <button onClick={handleTitleSave} className="text-success"><Check size={16}/></button>
            </div>
          ) : (
            <div className="flex items-center gap-2 group cursor-pointer" onClick={() => {
              setTempTitle(session?.title || "New session");
              setIsEditingTitle(true);
            }}>
              <h2 className="font-semibold text-foreground truncate max-w-[200px]">
                {session?.title || "New session"}
              </h2>
              {session && <Edit2 size={14} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />}
            </div>
          )}
          {session && (
            <div className="text-xs text-muted-foreground bg-white/5 py-1 px-2 rounded-md">
              {messages.length} messages
            </div>
          )}
        </div>
      </header>

      {/* Workspace Path Bar */}
      <div className="shrink-0 border-b border-border bg-surface px-4 py-2 flex items-center gap-2">
        <FolderOpen size={14} className="text-accent shrink-0" />
        <input
          type="text"
          value={workspacePath}
          onChange={(e) => onWorkspaceChange(e.target.value)}
          placeholder="Enter project folder path (e.g. C:/Users/you/Projects/my-app)"
          className="flex-1 text-xs bg-transparent text-foreground placeholder:text-muted-foreground/50 outline-none font-mono"
        />
        {workspacePath && (
          <span className="text-[10px] text-success bg-success/10 border border-success/20 px-1.5 py-0.5 rounded-md shrink-0">
            Active
          </span>
        )}
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="bg-destructive/10 border-b border-destructive/20 p-3 flex items-start gap-2 text-destructive text-sm shrink-0">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>{errorMsg}</p>
        </div>
      )}

      {/* Messages — this is the ONLY scrollable area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 min-h-0">
        {isLoadingSession && messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <span className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            <span className="text-sm">Loading conversation…</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center max-w-[600px] mx-auto w-full gap-8">
            <HollowMark size={88} />
            <div>
              <h1 className="sec-h mb-3" style={{ fontSize: "2.4rem", letterSpacing: "6px", color: "var(--whisper-primary)" }}>HollowNest</h1>
              <p className="text-muted-foreground italic">your coding agent — patient, quiet, here.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-4">
              {EXAMPLES.map((ex, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  onClick={() => {
                    setInput(ex);
                    if (textareaRef.current) textareaRef.current.focus();
                  }}
                  className="p-4 bg-surface border border-border rounded-xl text-left text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 hover:-translate-y-1 transition-all"
                >
                  {ex}
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          <AnimatePresence>
            {messages.map((m, i) => (
              <motion.div
                key={m.id || i}
                initial={{ opacity: 0, x: m.role === "user" ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex w-full min-w-0 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "user" ? (
                   <div className="bg-white/[0.06] text-foreground border border-border px-4 py-3 rounded-2xl rounded-tr-sm max-w-[70%] whitespace-pre-wrap text-sm leading-relaxed break-words">
                     {m.attachments && m.attachments.length > 0 && (
                       <div className="flex flex-wrap gap-2 mb-2">
                         {m.attachments.map((att, idx) => {
                           const isImage = att.mime_type?.startsWith("image/");
                           return (
                             <div key={idx} className="flex items-center gap-2 bg-black/20 rounded-lg px-2 py-1 text-xs max-w-[150px] overflow-hidden">
                               {isImage ? <ImageIcon size={14} className="shrink-0"/> : (att.mime_type?.startsWith("video/") ? <Film size={14} className="shrink-0"/> : <FileText size={14} className="shrink-0"/>)}
                               <span className="truncate">{att.original_name}</span>
                             </div>
                           );
                         })}
                       </div>
                     )}
                     {m.content}
                   </div>
                ) : (
                   <div className="flex flex-col gap-2 max-w-[85%] min-w-0">
                     <div className="bg-surface border border-border px-5 py-4 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm text-foreground overflow-x-auto">
                       {m.content ? (
                         <div className="prose prose-invert prose-p:my-2 prose-pre:my-0 max-w-none prose-pre:bg-transparent prose-pre:p-0 break-words overflow-wrap-anywhere">
                           <ReactMarkdown
                             components={{
                               code({ node, inline, className, children, ...props }: any) {
                                 const match = /language-(\w+)/.exec(className || "");
                                 return !inline && match ? (
                                   <div className="my-4 rounded-md overflow-hidden border border-border">
                                     <div className="bg-[var(--void-deep)] px-4 py-1.5 text-xs text-muted-foreground border-b border-border flex justify-between uppercase">
                                        {match[1]}
                                     </div>
                                     <SyntaxHighlighter
                                       {...props}
                                       style={vscDarkPlus}
                                       language={match[1]}
                                       PreTag="div"
                                       className="mt-0 pt-4 pb-4"
                                     >
                                       {String(children).replace(/\n$/, "")}
                                     </SyntaxHighlighter>
                                   </div>
                                 ) : (
                                   <code {...props} className="bg-white/10 px-1 py-0.5 rounded text-[13px] text-accent-foreground font-mono">
                                     {children}
                                   </code>
                                 );
                               },
                             }}
                           >
                             {m.content}
                           </ReactMarkdown>
                         </div>
                       ) : (
                         isStreaming && i === messages.length - 1 && (
                           <div className="flex gap-1 h-[20px] items-center">
                             <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                             <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                             <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce"></span>
                           </div>
                         )
                       )}
                     </div>
                     {m.content && !(isStreaming && i === messages.length - 1) && (
                       <div className="flex items-center gap-1 ml-0.5">
                         <button
                           onClick={() => handleSpeak(m)}
                           title={speakingMsgId === m.id ? "Stop reading" : "Read aloud"}
                           className="t-all flex items-center justify-center w-7 h-7 rounded-md text-[var(--whisper-ghost)] hover:text-[var(--whisper-secondary)] hover:bg-white/[0.05]"
                         >
                           {speakingMsgId === m.id ? <VolumeX size={14} /> : <Volume2 size={14} />}
                         </button>
                         <button
                           onClick={() => handleCopy(m)}
                           title={copiedMsgId === m.id ? "Copied" : "Copy message"}
                           className="t-all flex items-center justify-center w-7 h-7 rounded-md text-[var(--whisper-ghost)] hover:text-[var(--whisper-secondary)] hover:bg-white/[0.05]"
                         >
                           {copiedMsgId === m.id ? (
                             <Check size={14} className="text-[var(--silk-accent)]" />
                           ) : (
                             <Copy size={14} />
                           )}
                         </button>
                       </div>
                     )}
                     {!isStreaming && i === messages.length - 1 && session && (
                       <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase font-semibold tracking-wider opacity-70 ml-2">
                         <div className="w-1.5 h-1.5 rounded-full bg-accent"></div>
                         {session.model}
                       </div>
                     )}
                   </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        {/* Bottom spacer to ensure scroll room */}
        <div className="h-4 shrink-0" />
      </div>

      {/* Input */}
      <div className="p-4 bg-surface border-t border-border shrink-0">
        <div className="max-w-[800px] mx-auto w-full relative">
          
          {/* Pending Files Preview */}
          {pendingFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3 bg-background border border-border p-2 rounded-xl">
              {pendingFiles.map((file, idx) => {
                const isImage = file.type.startsWith("image/");
                return (
                  <div key={idx} className="relative group bg-surface border border-border rounded-lg px-3 py-2 flex items-center gap-2 text-xs text-foreground max-w-[200px]">
                    {isImage ? <ImageIcon size={14} className="text-accent shrink-0"/> : (file.type.startsWith("video/") ? <Film size={14} className="text-accent shrink-0"/> : <FileText size={14} className="text-accent shrink-0"/>)}
                    <span className="truncate">{file.name}</span>
                    <button 
                      onClick={() => removePendingFile(idx)}
                      className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full w-5 h-5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X size={10} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          <div className="relative flex items-end gap-2">
            {/* File Input */}
            <input 
              type="file" 
              multiple 
              hidden 
              ref={fileInputRef} 
              onChange={handleFileSelect}
              accept="image/*,video/*,application/pdf"
            />
            
            <Tooltip>
              <TooltipTrigger render={<div className="contents" />}>
                <Button 
                  size="icon" 
                  variant="ghost" 
                  className="w-10 h-[48px] shrink-0 text-muted-foreground hover:text-foreground mb-[-2px] rounded-xl"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isStreaming || isUploading}
                >
                  <Paperclip size={20} />
                </Button>
              </TooltipTrigger>
              <TooltipContent><p>Attach file (max 10MB)</p></TooltipContent>
            </Tooltip>

            <div className="mb-[-2px]">
              <VoiceButton
                onTranscript={(text) => {
                  setInput(text);
                  if (textareaRef.current) textareaRef.current.focus();
                }}
                disabled={isStreaming || isUploading}
              />
            </div>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (canSend) handleSend();
                }
              }}
              placeholder={isUploading ? "Uploading files..." : "Whisper to the void..."}
              disabled={isUploading}
              className="flex-1 bg-background border border-border rounded-xl px-4 py-3 pr-[50px] text-sm resize-none focus:outline-none focus:ring-1 focus:ring-accent max-h-[150px] min-h-[48px] overflow-y-auto placeholder:text-muted-foreground disabled:opacity-50"
              rows={1}
            />
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
            {isSpeaking && (
              <button
                type="button"
                onClick={stopSpeaking}
                className="w-8 h-8 rounded-lg bg-[var(--void-hover)] hover:bg-[var(--void-border-active)] text-[var(--whisper-muted)] hover:text-[var(--whisper-primary)] flex items-center justify-center transition-all"
                title="Stop speaking"
              >
                <span className="w-3 h-3 bg-current rounded-sm" />
              </button>
            )}
            <Tooltip>
              <TooltipTrigger render={<div className="contents" />}>
                <Button
                  size="icon"
                  className={`w-8 h-8 rounded-lg transition-all ${
                    !canSend
                      ? "bg-white/10 text-muted cursor-not-allowed" 
                      : "bg-accent text-accent-foreground hover:bg-accent/90"
                  }`}
                  onClick={handleSend}
                  disabled={!canSend}
                >
                  {isUploading ? (
                    <span className="w-3 h-3 border-2 border-white/50 border-t-white rounded-full animate-spin"></span>
                  ) : (
                    <Send size={14} className={isStreaming ? "opacity-50" : "ml-[2px]"} />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Send message (Enter)</p>
              </TooltipContent>
            </Tooltip>
          </div>
          </div>
        </div>
        {/* Status line — model selector sits at the bottom-right, Claude Code style */}
        <div className="max-w-[800px] mx-auto w-full mt-2 flex items-center justify-between gap-3">
          <span className="text-[10px] text-muted-foreground">
            {input.length > 500 ? `${input.length} characters` : ""}
          </span>
          <ProviderSelector
            provider={provider}
            model={model}
            onChange={onProviderChange}
            providersData={providersData}
          />
        </div>
      </div>
    </div>
  );
}
