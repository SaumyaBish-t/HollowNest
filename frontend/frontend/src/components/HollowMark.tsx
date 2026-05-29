// HollowNest logomark — abstract hollow vessel + silk-thread nest.
// Part of the Void Whisper design system.

interface HollowMarkProps {
  size?: number;
  stroke?: string;
  threads?: boolean;
  withBg?: boolean;
}

export function HollowMark({
  size = 40,
  stroke = "var(--whisper-primary)",
  threads = true,
  withBg = false,
}: HollowMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: "block", overflow: "visible" }}
    >
      {withBg && <rect width="64" height="64" rx="10" fill="var(--void-base)" />}

      {/* silk threads (nest) — drawn under the vessel */}
      {threads && (
        <g stroke={stroke} strokeWidth="0.55" opacity="0.55" strokeLinecap="round" fill="none">
          <path d="M6 28 Q 18 32 24 24" />
          <path d="M58 28 Q 46 33 40 24" />
          <path d="M8 38 Q 20 42 24 36" />
          <path d="M56 38 Q 44 42 40 36" />
          <path d="M10 50 Q 24 48 30 54" />
          <path d="M54 50 Q 40 48 34 54" />
          <path d="M14 24 L 50 24" opacity="0.35" strokeDasharray="0.4 2.4" />
          <path d="M12 44 L 52 44" opacity="0.3" strokeDasharray="0.4 2.4" />
        </g>
      )}

      {/* main hollow vessel */}
      <g stroke={stroke} fill="none" strokeLinecap="round" strokeLinejoin="round">
        <path
          d="M32 8.5 C 22.5 8.8, 15 16.5, 14.2 26 C 13.6 33, 15.4 40, 19.4 45.5 C 22 49.2, 24.5 52, 25.4 55.5"
          strokeWidth="1.5"
        />
        <path
          d="M32.4 8.5 C 41.8 9.1, 49.1 16.7, 49.8 26 C 50.3 33, 48.4 40, 44.4 45.6 C 41.7 49.4, 39.3 52.1, 38.4 55.6"
          strokeWidth="1.5"
        />
        <path d="M31 8.2 L 30.2 13 L 31.6 11.4 L 31.1 16 L 32.5 14" strokeWidth="0.8" opacity="0.85" />
        <path d="M25.6 54 Q 32 57.5 38.2 54.2" strokeWidth="1.1" opacity="0.7" />
        <path d="M19.5 33 Q 23 35.5 26.2 34" strokeWidth="0.5" opacity="0.55" />
        <path d="M44 33 Q 41 35.5 38.2 34" strokeWidth="0.5" opacity="0.55" />
      </g>

      {/* hollow eye voids */}
      <ellipse cx="25.5" cy="28.5" rx="2.2" ry="2.8" fill={stroke} />
      <ellipse cx="38.5" cy="28.5" rx="2.2" ry="2.8" fill={stroke} />
      <path d="M22 23 Q 32 19 42 23" stroke={stroke} strokeWidth="0.4" opacity="0.35" fill="none" />
    </svg>
  );
}

// Tiny favicon-scale mark — just the vessel silhouette, no threads.
export function HollowGlyph({ size = 16, stroke = "var(--whisper-primary)" }: { size?: number; stroke?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" style={{ display: "block" }}>
      <path
        d="M16 4 C 10 4.2, 6 9, 5.6 15.2 C 5.3 19.8, 7 23.8, 9.8 27 M16 4 C 22 4.2, 26 9, 26.4 15.2 C 26.7 19.8, 25 23.8, 22.2 27"
        stroke={stroke}
        strokeWidth="1.3"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="12.5" cy="14" r="1.3" fill={stroke} />
      <circle cx="19.5" cy="14" r="1.3" fill={stroke} />
    </svg>
  );
}
