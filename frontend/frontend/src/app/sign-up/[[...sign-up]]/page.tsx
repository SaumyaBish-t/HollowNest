import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { HollowMark } from "@/components/HollowMark";

export default function Page() {
  return (
    <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-background px-4 py-10">
      {/* Ambient backdrops */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_30%,rgba(200,200,220,0.10),transparent_60%),radial-gradient(circle_at_50%_80%,rgba(120,90,200,0.10),transparent_55%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-px bg-gradient-to-r from-transparent via-[color:var(--whisper-primary)]/40 to-transparent"
      />

      <div className="relative z-10 flex w-full max-w-[440px] flex-col items-center gap-8">
        {/* Brand */}
        <Link
          href="/"
          className="flex flex-col items-center gap-3 text-foreground transition-opacity hover:opacity-80"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-surface shadow-[0_0_40px_-10px_rgba(200,200,220,0.35)]">
            <HollowMark size={42} />
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-3xl font-semibold tracking-wide !text-white">
              HollowNest
            </span>
            <span className="text-xs uppercase tracking-[0.25em] !text-[#b8b8cc]">
              your AI workspace
            </span>
          </div>
        </Link>

        {/* Clerk card */}
        <SignUp
          appearance={{
            elements: {
              rootBox: "w-full",
              card:
                "w-full !bg-[#0f0f1e]/95 backdrop-blur-md !border !border-[rgba(200,200,220,0.18)] " +
                "!shadow-[0_30px_80px_-30px_rgba(0,0,0,0.8)] !rounded-2xl",
              headerTitle: "!text-white !text-xl !font-semibold",
              headerSubtitle: "!text-[#c8c8dc] !text-sm",
              socialButtonsBlockButton:
                "!border !border-[rgba(200,200,220,0.2)] !bg-[#16162a] hover:!bg-[#1f1f3a] !text-white",
              socialButtonsBlockButtonText: "!text-white !font-medium",
              dividerLine: "!bg-[rgba(200,200,220,0.18)]",
              dividerText: "!text-[#a8a8c2]",
              formFieldLabel: "!text-[#d0d0e0] !text-xs !uppercase !tracking-wider !font-medium",
              formFieldInput:
                "!bg-[#16162a] !border !border-[rgba(200,200,220,0.18)] !text-white " +
                "focus:!border-[#c8c8dc] focus:!ring-1 focus:!ring-[#c8c8dc] placeholder:!text-[#6a6a80]",
              formButtonPrimary:
                "!bg-[#c8c8dc] hover:!bg-[#d8d8ec] !text-[#0a0a14] !font-semibold !normal-case " +
                "!shadow-[0_8px_24px_-8px_rgba(200,200,220,0.5)]",
              footer: "!bg-transparent",
              footerActionText: "!text-[#c8c8dc]",
              footerActionLink: "!text-[#e8e8f4] hover:!text-white !font-semibold",
              identityPreviewText: "!text-white",
              identityPreviewEditButton: "!text-[#c8c8dc] hover:!text-white",
            },
          }}
        />

        <p className="text-center text-xs text-muted-foreground">
          New here? Bring your own API keys — we never store them on our servers.
        </p>
      </div>
    </main>
  );
}
