"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import html2canvas from "html2canvas";
import { Camera, ChevronDown, ChevronRight, TerminalSquare, AlertTriangle, CheckCircle2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { uploadCurrentScreenScreenshot } from "@/lib/api";

export interface ToolCallData {
  id: string;
  name: string;
  args: unknown;
  result?: string;
  status: "running" | "done" | "error";
  duration?: number;
}

interface ToolCallPanelProps {
  toolCalls: ToolCallData[];
}

async function captureWithScreenPicker(): Promise<Blob> {
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: { displaySurface: "browser" },
    audio: false,
  } as DisplayMediaStreamOptions);

  try {
    const video = document.createElement("video");
    video.srcObject = stream;
    video.muted = true;
    await video.play();

    await new Promise((resolve) => {
      if (video.readyState >= 2) resolve(undefined);
      else video.onloadeddata = () => resolve(undefined);
    });

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Could not create screenshot canvas.");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((result) => {
        if (result) resolve(result);
        else reject(new Error("Could not create screenshot image."));
      }, "image/png");
    });
  } finally {
    stream.getTracks().forEach((track) => track.stop());
  }
}

function ToolCallCard({ tc }: { tc: ToolCallData }) {
  const [expanded, setExpanded] = useState(false);
  const [showFullOutput, setShowFullOutput] = useState(false);

  const renderStatus = () => {
    if (tc.status === "running") {
      return (
        <Badge variant="outline" className="text-[var(--silk-accent)] border-[var(--void-border-active)] bg-white/[0.04] animate-pulse text-[10px]">
          running
        </Badge>
      );
    }
    if (tc.status === "error") {
      return (
        <Badge variant="outline" className="text-destructive border-destructive/30 bg-destructive/10 text-[10px] gap-1">
          <AlertTriangle size={10} /> error
        </Badge>
      );
    }
    return (
      <div className="flex items-center gap-2">
        {tc.duration && <span className="text-[10px] text-muted-foreground">{tc.duration}ms</span>}
        <Badge variant="outline" className="text-success border-success/30 bg-success/10 text-[10px] gap-1">
          <CheckCircle2 size={10} /> done
        </Badge>
      </div>
    );
  };

  const outputPreview = tc.result 
    ? (showFullOutput ? tc.result : tc.result.slice(0, 300) + (tc.result.length > 300 ? "..." : ""))
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      layout
      className="flex flex-col bg-surface border border-border rounded-lg overflow-hidden"
    >
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown size={14} className="text-muted-foreground" /> : <ChevronRight size={14} className="text-muted-foreground" />}
          <span className="font-mono text-xs font-semibold text-foreground tracking-tight">
            {tc.name}
          </span>
        </div>
        {renderStatus()}
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-border"
          >
            <div className="p-3 flex flex-col gap-3 bg-[var(--void-deep)]">
              <div>
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-1 block">Input</span>
                <pre className="bg-background border border-border p-2 rounded-md text-[11px] font-mono text-accent-foreground overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(tc.args, null, 2)}
                </pre>
              </div>
              
              {tc.result && (
                <div>
                  <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-1 block">Output</span>
                  <pre className="bg-background border border-border p-2 rounded-md text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                    {outputPreview}
                  </pre>
                  {tc.result.length > 300 && (
                    <button 
                      onClick={() => setShowFullOutput(!showFullOutput)}
                      className="text-[11px] text-accent hover:underline mt-1"
                    >
                      {showFullOutput ? "Show less" : "Show more"}
                    </button>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function ToolCallPanel({ toolCalls }: ToolCallPanelProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [captureStatus, setCaptureStatus] = useState("");
  const [isCapturing, setIsCapturing] = useState(false);

  // Auto-scroll the ScrollArea container — NOT scrollIntoView
  useEffect(() => {
    // ScrollArea wraps content in a [data-radix-scroll-area-viewport] element
    const viewport = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (viewport) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
    }
  }, [toolCalls]);

  const handleCaptureCurrentScreen = async () => {
    if (isCapturing) return;
    setIsCapturing(true);
    setCaptureStatus("");

    try {
      let blob: Blob;
      try {
        const canvas = await html2canvas(document.body, {
          backgroundColor: null,
          scale: window.devicePixelRatio || 1,
          useCORS: true,
          width: window.innerWidth,
          height: window.innerHeight,
          windowWidth: window.innerWidth,
          windowHeight: window.innerHeight,
          scrollX: window.scrollX,
          scrollY: window.scrollY,
        });

        blob = await new Promise<Blob>((resolve, reject) => {
          canvas.toBlob((result) => {
            if (result) resolve(result);
            else reject(new Error("Could not create screenshot image."));
          }, "image/png");
        });
      } catch {
        blob = await captureWithScreenPicker();
      }

      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      const result = await uploadCurrentScreenScreenshot(blob, `current-screen-${stamp}.png`);
      setCaptureStatus(`Saved: ${result.path}`);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Unknown error";
      setCaptureStatus(`Capture failed: ${message}`);
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <div className="w-[320px] flex flex-col h-full bg-surface border-l border-border shrink-0">
      <header className="h-[60px] p-4 border-b border-border flex items-center justify-between shrink-0 bg-surface">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <TerminalSquare size={16} className="text-accent" />
          Agent Activity
        </h3>
        <div className="flex items-center gap-2">
          {toolCalls.length > 0 && (
            <Badge variant="outline" className="text-muted-foreground border-border bg-background text-[10px]">
              {toolCalls.length} actions
            </Badge>
          )}
          <Button
            size="icon-sm"
            variant="outline"
            onClick={handleCaptureCurrentScreen}
            disabled={isCapturing}
            title="Capture current screen"
          >
            <Camera size={14} />
          </Button>
        </div>
      </header>

      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        {captureStatus && (
          <div className="mb-3 rounded-md border border-border bg-background p-2 text-[11px] text-muted-foreground break-words">
            {captureStatus}
          </div>
        )}
        {toolCalls.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center pt-20">
            <TerminalSquare size={32} className="text-muted border border-border bg-background p-1.5 rounded-lg mb-3" />
            <p className="text-sm text-muted-foreground max-w-[200px]">
              Tool calls will appear here as the agent works
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 pb-8">
            {toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} tc={tc} />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
