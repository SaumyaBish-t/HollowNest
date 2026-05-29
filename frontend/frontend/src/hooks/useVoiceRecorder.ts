"use client"
import { useState, useRef, useCallback } from "react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export type RecordingState = "idle" | "recording" | "transcribing" | "error"

interface UseVoiceRecorderReturn {
  state: RecordingState
  startRecording: () => Promise<void>
  stopRecording: () => void
  error: string | null
}

export function useVoiceRecorder(
  onTranscript: (text: string) => void
): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecordingState>("idle")
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4"

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: mimeType })

        if (blob.size < 1000) {
          setState("idle")
          return
        }

        setState("transcribing")
        try {
          const formData = new FormData()
          formData.append("audio", blob, "recording.webm")

          const res = await fetch(`${API_URL}/voice/transcribe`, {
            method: "POST",
            body: formData,
          })

          if (!res.ok) {
            const err = await res.json()
            throw new Error(err.detail || "Transcription failed")
          }

          const data = await res.json()
          if (data.text?.trim()) onTranscript(data.text.trim())
          setState("idle")
        } catch (err: any) {
          setError(err.message)
          setState("error")
          setTimeout(() => setState("idle"), 3000)
        }
      }

      mediaRecorder.start(250)
      setState("recording")
    } catch (err: any) {
      setError(
        err.name === "NotAllowedError"
          ? "Microphone permission denied. Allow mic access and try again."
          : err.message
      )
      setState("error")
      setTimeout(() => setState("idle"), 3000)
    }
  }, [onTranscript])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
    }
  }, [])

  return { state, startRecording, stopRecording, error }
}
