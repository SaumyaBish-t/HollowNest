"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, Plus, Trash2, PlugZap } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { HollowMark } from "@/components/HollowMark";
import type { Session } from "@/lib/api";

interface SessionSidebarProps {
  sessions: Session[];
  selectedSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onOpenToolStore?: () => void;
  connectedToolCount?: number;
}

function timeAgo(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.round(diffMs / 60000);
  const diffHrs = Math.round(diffMins / 60);
  const diffDays = Math.round(diffHrs / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays === 1) return "Yesterday";
  return `${diffDays}d ago`;
}

export default function SessionSidebar({
  sessions,
  selectedSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenToolStore,
  connectedToolCount = 0,
}: SessionSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = sessions.filter((s) =>
    (s.title || "New session").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="w-full flex flex-col h-full bg-surface border-r border-border shrink-0">
      {/* Logo — its own header bar, aligned with the chat header */}
      <div className="h-[60px] shrink-0 border-b border-border flex items-center gap-2.5 px-4 overflow-hidden">
        <HollowMark size={42} threads={false} />
        <h1 className="wordmark">HollowNest</h1>
      </div>

      <div className="p-4 flex flex-col gap-3 border-b border-border shrink-0">
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search the past..."
            className="pl-10 h-11 text-sm bg-background border-border"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <Button
            onClick={onNewSession}
            className="flex-1 h-11 text-sm bg-accent text-accent-foreground hover:bg-accent/90"
          >
            <Plus size={18} className="mr-2" />
            New Session
          </Button>
        </div>

        {/* Tool Store Button */}
        {onOpenToolStore && (
          <button
            onClick={onOpenToolStore}
            className="flex items-center justify-between w-full px-3.5 py-3 rounded-lg border border-border bg-background hover:bg-white/5 hover:border-accent/30 transition-all group"
          >
            <div className="flex items-center gap-2.5">
              <PlugZap size={18} className="text-accent group-hover:text-accent" />
              <span className="text-base font-medium text-foreground">Tool Store</span>
            </div>
            {connectedToolCount > 0 && (
              <Badge variant="outline" className="text-[11px] text-success border-success/30 bg-success/10">
                {connectedToolCount} active
              </Badge>
            )}
          </button>
        )}
      </div>

      <ScrollArea className="flex-1 min-h-0 p-2">
        <div className="flex flex-col gap-1 pb-4">
          {filtered.map((s, i) => {
            const isSelected = s.id === selectedSessionId;

            return (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.05, 0.5), duration: 0.2 }}
                onClick={() => onSelectSession(s.id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  onDeleteSession(s.id);
                }}
                className={`group relative flex flex-col gap-1.5 p-3.5 rounded-lg cursor-pointer transition-colors ${
                  isSelected
                    ? "bg-white/10"
                    : "hover:bg-white/5"
                }`}
              >
                {isSelected && (
                  <motion.div
                    layoutId="active-session-indicator"
                    className="absolute left-0 top-2 bottom-2 w-1 bg-accent rounded-r-md"
                  />
                )}
                
                <div className="flex items-center justify-between">
                  <span className="font-medium text-base truncate pr-6 text-foreground">
                    {s.title || "New session"}
                  </span>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(s.id);
                    }}
                    className="absolute right-2 opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-destructive transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="tag">{s.provider}</span>
                  <span className="timestamp">{timeAgo(s.created_at)}</span>
                </div>
              </motion.div>
            );
          })}
          {filtered.length === 0 && (
            <div className="p-4 text-center items-center flex flex-col gap-2 mt-10">
              <span className="text-sm text-muted-foreground">No sessions found</span>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
