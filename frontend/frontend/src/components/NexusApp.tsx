"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Settings, PlugZap } from "lucide-react";
import { useAuth, UserButton } from "@clerk/nextjs";
import SessionSidebar from "./SessionSidebar";
import ChatPanel from "./ChatPanel";
import ToolCallPanel from "./ToolCallPanel";
import ToolStore from "./ToolStore";
import { ToolCallData } from "./ToolCallPanel";
import { getSessions, getProviders, Session, deleteSession, setAuthTokenGetter } from "@/lib/api";
import {
  getConnectedTools,
  getWorkspacePath,
  saveWorkspacePath,
  setKeyUserScope,
  migrateLegacyKeysIntoScope,
} from "@/lib/keys";

interface NexusAppProps {
  initialSessionId?: string | null;
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function NexusApp({ initialSessionId = null }: NexusAppProps) {
  const router = useRouter();
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  const [scopeReady, setScopeReady] = useState(false);

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(initialSessionId);
  const [selectedProvider, setSelectedProvider] = useState("cerebras");
  const [selectedModel, setSelectedModel] = useState("gpt-oss-120b");
  const [showToolStore, setShowToolStore] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const [sessions, setSessions] = useState<Session[]>([]);
  const [providersData, setProvidersData] = useState<Record<string, { label: string; models: string[] }>>({});
  
  const [toolCalls, setToolCalls] = useState<ToolCallData[]>([]);
  const [activeTab, setActiveTab] = useState<"sessions" | "chat" | "activity">("chat");

  // Track connected tools — this list is sent with each agent request
  const [connectedTools, setConnectedTools] = useState<string[]>([]);
  const [workspacePath, setWorkspacePath] = useState("");

  const refreshSessions = useCallback(async () => {
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const data = await getSessions();
        setSessions(data);
        return;
      } catch(e) {
        if (attempt < 3) {
          await wait(400 * attempt);
          continue;
        }
        console.warn("Session list refresh failed; keeping current sessions.", e);
      }
    }
  }, []);

  // Install the Clerk token getter so every authedFetch in lib/api.ts
  // attaches Authorization: Bearer <jwt> to its request.
  useEffect(() => {
    if (!isLoaded) return;
    setAuthTokenGetter(isSignedIn ? () => getToken() : null);
    return () => setAuthTokenGetter(null);
  }, [isLoaded, isSignedIn, getToken]);

  // Scope all localStorage reads/writes (API keys, tool credentials,
  // connected-tool list, workspace path) to the current Clerk user so two
  // accounts on the same browser cannot see each other's keys. First time
  // a user signs in on this browser any legacy un-scoped entries written
  // by older builds are migrated into the user's scope.
  useEffect(() => {
    if (!isLoaded) return;
    if (isSignedIn && userId) {
      setKeyUserScope(userId);
      migrateLegacyKeysIntoScope();
    } else {
      setKeyUserScope(null);
    }
    setConnectedTools(getConnectedTools());
    setWorkspacePath(getWorkspacePath());
    setScopeReady(true);
    return () => setKeyUserScope(null);
  }, [isLoaded, isSignedIn, userId]);

  // Load initial data — wait for the scope to be installed first so the
  // X-API-Keys header on getProviders/getSessions can pull from the right
  // localStorage bucket.
  useEffect(() => {
    if (!scopeReady) return;
    getProviders()
      .then(setProvidersData)
      .catch(e => console.error("Failed to load providers", e));

    refreshSessions();
  }, [scopeReady, refreshSessions]);

  // Update URL and state on session change
  useEffect(() => {
    if (initialSessionId !== undefined) {
      setSelectedSessionId(initialSessionId);
    }
  }, [initialSessionId]);

  const refreshConnectedTools = useCallback(() => {
    setConnectedTools(getConnectedTools());
  }, []);

  // Use window.history so Next.js does NOT remount the component tree
  const handleSelectSession = (id: string) => {
    setSelectedSessionId(id);
    setToolCalls([]); // clear activity on session switch
    window.history.pushState({}, '', `/sessions/${id}`);
    setActiveTab("chat"); // snap back to chat on mobile
  };

  const handleNewSession = () => {
    setSelectedSessionId(null);
    setToolCalls([]);
    window.history.pushState({}, '', `/`);
    setActiveTab("chat");
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      if (selectedSessionId === id) {
        handleNewSession();
      } else {
        refreshSessions();
      }
    } catch(e) {
      console.error("Failed to delete session", e);
    }
  };

  const handleProviderChange = (provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
  };

  const handleToolCall = (id: string, name: string, args: any) => {
    setToolCalls(prev => [...prev, { id, name, args, status: "running" }]);
  };

  const handleToolResult = (id: string, name: string, result: string) => {
    setToolCalls(prev => {
      const copy = [...prev];
      const idx = copy.findLastIndex(tc => tc.status === "running" && tc.name === name);
      if (idx !== -1) {
        copy[idx] = { ...copy[idx], result, status: "done", duration: Math.floor(Math.random() * 500) + 100 };
      }
      return copy;
    });
  };

  const handleAgentDone = () => {
    setToolCalls(prev => prev.map(tc => tc.status === "running" ? { ...tc, status: "error" } : tc));
    refreshSessions();
  };

  return (
    <div className="flex flex-col h-screen w-full bg-background overflow-hidden relative text-foreground">
      
      {/* Mobile Tabs */}
      <div className="md:hidden flex h-14 bg-surface border-b border-border items-center justify-around shrink-0 px-2 z-40">
        <button 
          onClick={() => setActiveTab("sessions")} 
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === "sessions" ? "bg-accent/20 text-accent" : "text-muted-foreground"}`}
        >
          Sessions
        </button>
        <button 
          onClick={() => setActiveTab("chat")} 
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === "chat" ? "bg-accent/20 text-accent" : "text-muted-foreground"}`}
        >
          Chat
        </button>
        <button 
          onClick={() => setActiveTab("activity")} 
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === "activity" ? "bg-accent/20 text-accent" : "text-muted-foreground"}`}
        >
          Activity
        </button>
      </div>

      {/* Panels container */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar Layout Container */}
        <div className={`
          flex h-full transition-all duration-300 bg-surface
          ${activeTab === "sessions" ? "w-full" : sidebarOpen ? "w-0 md:w-[360px]" : "w-0 md:w-0"}
          absolute md:relative z-20
          overflow-hidden
        `}>
          <SessionSidebar 
            sessions={sessions} 
            selectedSessionId={selectedSessionId} 
            onSelectSession={handleSelectSession} 
            onNewSession={() => { console.log("New Session Clicked"); handleNewSession(); }}
            onDeleteSession={handleDeleteSession}
            onOpenToolStore={() => { console.log("Tool Store Triggered"); setShowToolStore(true); }}
            connectedToolCount={connectedTools.length}
          />
        </div>

        {/* Main Content Area */}
        <div className={`
          flex-1 min-w-0 flex flex-col relative z-10
          ${activeTab === "chat" ? "opacity-100 pointer-events-auto" : "opacity-0 md:opacity-100 pointer-events-none md:pointer-events-auto"}
        `}>
          <ChatPanel 
            sessionId={selectedSessionId}
            provider={selectedProvider}
            model={selectedModel}
            onProviderChange={handleProviderChange}
            providersData={providersData}
            connectedTools={connectedTools}
            workspacePath={workspacePath}
            onWorkspaceChange={(path) => { setWorkspacePath(path); saveWorkspacePath(path); }}
            onSessionCreated={(id) => {
              setSelectedSessionId(id);
              window.history.pushState({}, '', `/sessions/${id}`);
              refreshSessions();
            }}
            onToolCall={handleToolCall}
            onToolResult={handleToolResult}
            onDone={handleAgentDone}
            onToggleSidebar={() => setSidebarOpen((o) => !o)}
            sidebarOpen={sidebarOpen}
          />
        </div>

        {/* Right Sidebar */}
        <div className={`
          h-full bg-surface border-l border-border transition-all duration-300
          ${activeTab === "activity" ? "w-full" : "w-0 md:w-[320px]"}
          absolute md:relative z-20 right-0 overflow-hidden
        `}>
          <ToolCallPanel toolCalls={toolCalls} />
        </div>
      </div>


      {showToolStore && (
        <ToolStore
          isOpen={showToolStore}
          onOpenChange={setShowToolStore}
          onToolsChanged={refreshConnectedTools}
        />
      )}

      {/* Account menu — floating top-right */}
      <div className="absolute top-3 right-4 z-50">
        <UserButton />
      </div>
    </div>
  );
}
