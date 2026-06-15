import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "HollowNest — AI Workspace",
  description: "Your AI workspace — patient, quiet, here. Powered by multiple AI engines.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <ClerkProvider
          appearance={{
            variables: {
              colorPrimary: "#c8c8dc",
              colorBackground: "#0d0d1a",
              colorText: "#f0f0fa",
              colorTextSecondary: "#a8a8c2",
              colorTextOnPrimaryBackground: "#0d0d1a",
              colorNeutral: "#e8e8f4",
              colorInputBackground: "#16162a",
              colorInputText: "#f0f0fa",
              colorDanger: "#ff7a90",
              colorSuccess: "#7adc9c",
              colorWarning: "#f5c46b",
              colorShimmer: "rgba(200,200,220,0.08)",
              borderRadius: "0.75rem",
              fontFamily: "var(--font-sans, ui-sans-serif, system-ui, sans-serif)",
              fontSize: "0.95rem",
            },
          }}
        >
          {/* Ambient void glow */}
          <div aria-hidden="true" className="void-glow" />

          {/* Drifting moth particles */}
          <div className="moth-field" aria-hidden="true">
            <div className="moth m1" />
            <div className="moth m2" />
            <div className="moth m3" />
          </div>

          <TooltipProvider>
            <div className="relative h-screen w-full overflow-hidden text-foreground">
              {children}
            </div>
          </TooltipProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
