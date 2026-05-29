"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Lock, Unlock, Key, ExternalLink, ArrowRight } from "lucide-react";
import {
  hasKey,
  getKey,
  saveKey,
  PROVIDER_LABELS,
  PROVIDER_KEY_LINKS,
} from "@/lib/keys";

interface ProviderInfo {
  label: string;
  models: string[];
  has_env_key?: boolean;
}

interface ProviderSelectorProps {
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
  providersData: Record<string, ProviderInfo>;
}

// Every provider now shows curated preset chips — no custom-model input.
const CUSTOM_MODEL_PROVIDERS: string[] = [];

// Example model IDs shown as input placeholders.
const MODEL_HINT: Record<string, string> = {
  openai: "e.g. gpt-4o",
  anthropic: "e.g. claude-sonnet-4-5",
  openrouter: "e.g. meta-llama/llama-3.3-70b-instruct",
  qwen: "e.g. qwen-plus",
  mistral: "e.g. codestral-latest",
};

export default function ProviderSelector({
  provider,
  model,
  onChange,
  providersData,
}: ProviderSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [keyPanel, setKeyPanel] = useState<string | null>(null);
  const [keyValue, setKeyValue] = useState("");
  const [modelDrafts, setModelDrafts] = useState<Record<string, string>>({});
  // Bump to re-read localStorage keys after an edit.
  const [, forceKeyRefresh] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setKeyPanel(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedLabel = providersData[provider]?.label || PROVIDER_LABELS[provider] || provider;

  // A provider is active when a key exists — server (.env) or browser.
  const isActive = (provKey: string) =>
    !!providersData[provKey]?.has_env_key || hasKey(provKey);

  const toggleKeyPanel = (provKey: string) => {
    if (keyPanel === provKey) {
      setKeyPanel(null);
    } else {
      setKeyValue(getKey(provKey));
      setKeyPanel(provKey);
    }
  };

  const draftFor = (provKey: string) =>
    modelDrafts[provKey] !== undefined
      ? modelDrafts[provKey]
      : provider === provKey
        ? model
        : "";

  const applyCustomModel = (provKey: string) => {
    const id = draftFor(provKey).trim();
    if (!id) return;
    onChange(provKey, id);
    setIsOpen(false);
    setKeyPanel(null);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Status-line model pill */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="t-all flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--void-border-active)] bg-transparent hover:bg-[var(--void-hover)]"
      >
        <span
          className="pulse-dot"
          style={{ background: "var(--silk-accent)", width: 6, height: 6 }}
        />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {selectedLabel}
        </span>
        <span className="font-mono text-xs text-foreground truncate max-w-[170px]">
          {model}
        </span>
        <ChevronDown
          size={13}
          className={`text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full right-0 mb-2 w-[440px] max-h-[74vh] overflow-y-auto bg-surface border border-border rounded-lg shadow-xl p-3 flex flex-col gap-2 z-50"
          >
            <div className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Choose model
            </div>

            {Object.entries(providersData).map(([provKey, pData]) => {
              const active = isActive(provKey);
              const keyOpen = keyPanel === provKey;
              const isCustom = CUSTOM_MODEL_PROVIDERS.includes(provKey);

              return (
                <div
                  key={provKey}
                  className="rounded-md border border-transparent hover:border-border transition-colors"
                >
                  {/* Provider header row */}
                  <div className="flex items-center justify-between px-2 pt-2 pb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ background: active ? "var(--silk-accent)" : "var(--whisper-ghost)" }}
                      />
                      <span className="font-semibold text-sm text-foreground truncate">
                        {pData.label}
                      </span>
                      {active ? (
                        <span className="flex items-center gap-1 text-[11px] text-success">
                          <Unlock size={12} /> active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                          <Lock size={12} /> needs key
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => toggleKeyPanel(provKey)}
                      title="Manage API key"
                      className="t-all flex items-center gap-1 px-2 py-1 rounded-md border border-border hover:bg-white/[0.06] text-[11px] font-medium shrink-0"
                    >
                      <Key
                        size={13}
                        className={active ? "text-success" : "text-muted-foreground"}
                      />
                      <span className={active ? "text-success" : "text-muted-foreground"}>
                        {active ? "Key set" : "Add key"}
                      </span>
                    </button>
                  </div>

                  {/* Model selection */}
                  {isCustom ? (
                    active ? (
                      // Custom providers: type the exact model ID to use.
                      <div className="flex items-center gap-1.5 px-2 pb-2">
                        <input
                          type="text"
                          value={draftFor(provKey)}
                          onChange={(e) =>
                            setModelDrafts((prev) => ({ ...prev, [provKey]: e.target.value }))
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              applyCustomModel(provKey);
                            }
                          }}
                          placeholder={`Model ID — ${MODEL_HINT[provKey] || "type a model name"}`}
                          className="flex-1 bg-background border border-border rounded-md px-2 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                        />
                        <button
                          onClick={() => applyCustomModel(provKey)}
                          disabled={!draftFor(provKey).trim()}
                          className="t-all flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-accent text-accent-foreground text-xs font-semibold disabled:opacity-35 disabled:cursor-not-allowed"
                        >
                          Use <ArrowRight size={12} />
                        </button>
                      </div>
                    ) : (
                      <div className="px-2 pb-2 text-xs text-muted-foreground italic">
                        Add your API key, then enter the model ID you want to use.
                      </div>
                    )
                  ) : (
                    // Preset providers: pick from curated model chips.
                    <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                      {pData.models.map((m) => {
                        const selected = provider === provKey && model === m;
                        return (
                          <button
                            key={m}
                            disabled={!active}
                            onClick={() => {
                              onChange(provKey, m);
                              setIsOpen(false);
                              setKeyPanel(null);
                            }}
                            title={active ? m : "Add an API key to enable this model"}
                            className={`t-all text-xs px-2.5 py-1.5 rounded-md border font-mono transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${
                              selected
                                ? "bg-accent/20 border-accent/50 text-foreground"
                                : "bg-background border-border text-muted-foreground hover:text-foreground hover:border-white/20"
                            }`}
                          >
                            {m}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* API key panel */}
                  <AnimatePresence>
                    {keyOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="px-2 pb-3">
                          <div className="flex items-center justify-between mb-1">
                            <label className="text-[11px] text-muted-foreground">
                              {providersData[provKey]?.has_env_key
                                ? "A server key is configured — adding one here overrides it"
                                : "Paste your API key — one per line"}
                            </label>
                            {PROVIDER_KEY_LINKS[provKey] && (
                              <a
                                href={PROVIDER_KEY_LINKS[provKey]}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] text-accent hover:underline flex items-center gap-1"
                              >
                                Get key <ExternalLink size={11} />
                              </a>
                            )}
                          </div>
                          <textarea
                            value={keyValue}
                            autoFocus
                            onChange={(e) => {
                              setKeyValue(e.target.value);
                              saveKey(provKey, e.target.value);
                              forceKeyRefresh((n) => n + 1);
                            }}
                            placeholder={`Paste your ${pData.label} key(s)...`}
                            rows={2}
                            className="w-full bg-background border border-border rounded-md px-2 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                          />
                          <p className="text-[10px] text-muted-foreground/70 italic mt-1">
                            Stored only in your browser. Paste multiple keys for auto-rotation.
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
