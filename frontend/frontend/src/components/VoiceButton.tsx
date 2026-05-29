"use client"
import { useEffect } from "react"
import { Mic, MicOff, Loader2 } from "lucide-react"
import { useVoiceRecorder, RecordingState } from "@/hooks/useVoiceRecorder"

interface VoiceButtonProps {
  onTranscript: (text: string) => void
  disabled?: boolean
}

export default function VoiceButton({ onTranscript, disabled }: VoiceButtonProps) {
  const { state, startRecording, stopRecording, error } = useVoiceRecorder(onTranscript)

  const isRecording = state === "recording"
  const isTranscribing = state === "transcribing"

  useEffect(() => () => stopRecording(), [stopRecording])

  const handleClick = () => {
    if (disabled || isTranscribing) return
    if (isRecording) stopRecording()
    else startRecording()
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isTranscribing}
        title={
          isRecording ? "Click to stop recording"
          : isTranscribing ? "Transcribing..."
          : "Click to speak"
        }
        className={`
          relative w-9 h-9 rounded-lg flex items-center justify-center
          transition-all duration-150 focus:outline-none
          ${isRecording
            ? "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30"
            : isTranscribing
            ? "bg-[#252525] text-[#6366F1] cursor-wait"
            : "bg-[#252525] hover:bg-[#2E2E2E] text-[#71717A] hover:text-white"
          }
          ${disabled ? "opacity-40 cursor-not-allowed" : ""}
        `}
      >
        {isTranscribing ? (
          <Loader2 size={16} className="animate-spin" />
        ) : isRecording ? (
          <>
            <span className="absolute inset-0 rounded-lg bg-red-500 animate-ping opacity-30" />
            <MicOff size={16} />
          </>
        ) : (
          <Mic size={16} />
        )}
      </button>

      {error && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2
                        bg-red-900 text-red-200 text-xs rounded px-2 py-1
                        whitespace-nowrap z-50 max-w-[200px] text-center">
          {error}
        </div>
      )}
    </div>
  )
}
