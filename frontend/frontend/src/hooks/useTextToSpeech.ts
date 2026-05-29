"use client"
import { useCallback, useEffect, useState } from "react"

export function useTextToSpeech() {
  const [speaking, setSpeaking] = useState(false)

  // Chrome populates voices asynchronously — warm them up on mount.
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return
    const warm = () => window.speechSynthesis.getVoices()
    warm()
    window.speechSynthesis.addEventListener?.("voiceschanged", warm)
    return () =>
      window.speechSynthesis.removeEventListener?.("voiceschanged", warm)
  }, [])

  // Reflect the engine's real state, and keep it alive — Chrome silently
  // cuts off long utterances after ~15s unless nudged out of "paused".
  useEffect(() => {
    if (!speaking) return
    const id = setInterval(() => {
      const synth = window.speechSynthesis
      if (!synth) return
      if (!synth.speaking && !synth.pending) {
        setSpeaking(false)
      } else if (synth.paused) {
        synth.resume()
      }
    }, 250)
    return () => clearInterval(id)
  }, [speaking])

  const stop = useCallback(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [])

  const speak = useCallback((text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return
    const synth = window.speechSynthesis

    const clean = text
      .replace(/```[\s\S]*?```/g, " code block ")
      .replace(/`[^`]+`/g, "")
      .replace(/#{1,6}\s/g, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/\n+/g, ". ")
      .trim()
    if (!clean) return

    // Clear anything queued first.
    synth.cancel()

    const utterance = new SpeechSynthesisUtterance(clean)
    utterance.rate = 1.05
    utterance.pitch = 1.0
    utterance.volume = 1.0

    const voices = synth.getVoices()
    const preferred = voices.find(
      (v) =>
        v.name.includes("Google US English") ||
        v.name.includes("Samantha") ||
        v.name.includes("Daniel") ||
        (v.lang === "en-US" && !v.name.includes("compact"))
    )
    if (preferred) utterance.voice = preferred

    utterance.onstart = () => setSpeaking(true)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)

    setSpeaking(true)

    // Chrome quirk: a speak() fired in the same frame as cancel() is often
    // dropped. Defer a tick, and resume() in case the engine is wedged.
    setTimeout(() => {
      try {
        synth.resume()
      } catch {
        /* no-op */
      }
      synth.speak(utterance)
    }, 70)
  }, [])

  return { speak, stop, speaking }
}
