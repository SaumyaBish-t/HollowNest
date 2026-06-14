"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plug, PlugZap, Check, ExternalLink,
  FileText, FilePlus, Folder, Terminal, Globe, Search,
  GitBranch, Database, Zap, Shield, RefreshCw, Layers
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getToolsMetadata, ToolMetadata } from "@/lib/api";
import {
  isToolConnected, connectTool, disconnectTool,
  saveToolCredential, getToolCredential,
} from "@/lib/keys";

interface ToolStoreProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onToolsChanged: () => void;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  "file-text": <FileText size={20} />,
  "file-plus": <FilePlus size={20} />,
  "folder": <Folder size={20} />,
  "terminal": <Terminal size={20} />,
  "globe": <Globe size={20} />,
  "search": <Search size={20} />,
  "github": <GitBranch size={20} />,
  "database": <Database size={20} />,
  "zap": <Zap size={20} className="text-yellow-400" />,
  "refresh-cw": <RefreshCw size={20} className="text-indigo-400" />,
  "layers": <Layers size={20} className="text-rose-400" />,
};

function ToolCard({
  toolId,
  meta,
  onConnectionChange,
}: {
  toolId: string;
  meta: ToolMetadata;
  onConnectionChange: () => void;
}) {
  const isBuiltin = meta.category === "builtin";
  const [connected, setConnected] = useState(isBuiltin || isToolConnected(toolId));
  const [expanded, setExpanded] = useState(false);
  const [credValues, setCredValues] = useState<Record<string, string>>({});
  const [justSaved, setJustSaved] = useState(false);

  // Load saved credentials on mount
  useEffect(() => {
    const loaded: Record<string, string> = {};
    meta.credentials.forEach((c) => {
      loaded[c.key] = getToolCredential(c.key);
    });
    setCredValues(loaded);
  }, [meta.credentials]);

  const handleConnect = () => {
    meta.credentials.forEach((c) => {
      saveToolCredential(c.key, credValues[c.key] || "");
    });
    connectTool(toolId);
    setConnected(true);
    setExpanded(false);
    setJustSaved(true);
    setTimeout(() => setJustSaved(false), 2000);
    onConnectionChange();
  };

  const handleDisconnect = () => {
    meta.credentials.forEach((c) => {
      saveToolCredential(c.key, "");
    });
    disconnectTool(toolId);
    setConnected(false);
    setCredValues({});
    onConnectionChange();
  };

  const allCredsFilled = meta.credentials.every(
    (c) => (credValues[c.key] || "").trim().length > 0
  );

  return (
    <motion.div
      layout
      className={`rounded-xl border transition-all ${
        connected
          ? "border-success/30 bg-success/5"
          : expanded
            ? "border-accent/40 bg-accent/5"
            : "border-border bg-surface hover:border-border/80"
      }`}
    >
      {/* Header */}
      <div
        className={`flex items-center gap-3 p-4 ${!isBuiltin && !connected ? "cursor-pointer" : ""}`}
        onClick={() => !isBuiltin && !connected && setExpanded(!expanded)}
      >
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
          connected ? "bg-success/20 text-success" : "bg-white/5 text-muted-foreground"
        }`}>
          {ICON_MAP[meta.icon] || <Zap size={20} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-foreground">{meta.name}</span>
            {isBuiltin ? (
              <Badge variant="outline" className="text-[10px] text-muted-foreground border-border gap-1">
                <Shield size={8} /> Built-in
              </Badge>
            ) : connected ? (
              <Badge variant="outline" className="text-[10px] text-success border-success/30 bg-success/10 gap-1">
                <Check size={8} /> Connected
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] text-muted-foreground border-border">
                Not connected
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{meta.description}</p>
        </div>

        {!isBuiltin && !connected && (
          <div className="shrink-0">
            <PlugZap size={16} className={`transition-transform ${expanded ? "rotate-90 text-accent" : "text-muted-foreground"}`} />
          </div>
        )}
      </div>

      {/* Disconnect bar for connected tools */}
      {!isBuiltin && connected && (
        <div className="px-4 pb-3">
          <button
            onClick={handleDisconnect}
            className="w-full text-xs text-destructive/70 hover:text-destructive border border-destructive/20 hover:border-destructive/40 hover:bg-destructive/10 transition-all px-3 py-2 rounded-lg flex items-center justify-center gap-1.5"
          >
            <Plug size={12} />
            Disconnect {meta.name}
          </button>
        </div>
      )}

      {/* Credential inputs (expandable) */}
      <AnimatePresence>
        {expanded && !isBuiltin && !connected && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 flex flex-col gap-3 border-t border-border/50 pt-3">
              {meta.credentials.map((cred) => (
                <div key={cred.key} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-muted-foreground">{cred.label}</label>
                    {cred.link && (
                      <a
                        href={cred.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-accent hover:underline flex items-center gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Get key <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                  <div className="relative">
                    <textarea
                      value={credValues[cred.key] || ""}
                      onChange={(e) => setCredValues((prev) => ({ ...prev, [cred.key]: e.target.value }))}
                      placeholder={cred.placeholder}
                      rows={3}
                      className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent font-mono text-foreground"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div className="absolute right-2 top-2 text-[10px] text-muted-foreground bg-surface/80 px-1 rounded pointer-events-none">
                      Supports Multi-Key (one per line)
                    </div>
                  </div>
                </div>
              ))}

              <Button
                onClick={(e) => { e.stopPropagation(); handleConnect(); }}
                disabled={!allCredsFilled}
                className="w-full bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed gap-2 h-9 text-sm"
              >
                <Plug size={14} />
                Connect {meta.name}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Just-saved confirmation */}
      <AnimatePresence>
        {justSaved && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="px-4 pb-3 flex items-center gap-2 text-success text-xs"
          >
            <Check size={14} /> Connected successfully! The agent can now use this tool.
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function ToolStore({ isOpen, onOpenChange, onToolsChanged }: ToolStoreProps) {
  const [toolsMeta, setToolsMeta] = useState<Record<string, ToolMetadata>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      getToolsMetadata()
        .then((tools) => setToolsMeta(tools))
        .catch((e) => console.error("Failed to load tools", e))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  const builtinTools = Object.entries(toolsMeta).filter(([, m]) => m.category === "builtin");
  const externalTools = Object.entries(toolsMeta).filter(([, m]) => m.category === "external");

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] sm:max-w-[900px] lg:max-w-[1000px] max-h-[85vh] overflow-y-auto overflow-x-hidden bg-background border-border text-foreground">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <PlugZap size={24} className="text-accent" />
            Tool Store
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Connect external tools and review the agent&apos;s built-in abilities. Credentials are stored locally in your browser. Manage AI models and API keys from the model selector below the chat.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-12 flex items-center justify-center">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce" />
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-8 mt-2">
            {/* External tools (user must connect) */}
            {externalTools.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-4 flex items-center gap-2 px-1">
                  <div className="w-1 h-3 bg-amber-400 rounded-full" />
                  External Tool Integrations
                </h3>
                <div className="flex flex-col gap-2">
                  {externalTools.map(([id, meta]) => (
                    <ToolCard key={id} toolId={id} meta={meta} onConnectionChange={onToolsChanged} />
                  ))}
                </div>
              </div>
            )}

            {/* Built-in tools (always on) */}
            {builtinTools.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-4 flex items-center gap-2 px-1">
                  <div className="w-1 h-3 bg-blue-400 rounded-full" />
                  Standard System Tools
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-muted-foreground/60">
                  {builtinTools.map(([id, meta]) => (
                    <ToolCard key={id} toolId={id} meta={meta} onConnectionChange={onToolsChanged} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
