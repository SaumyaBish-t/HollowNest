import type { Metadata } from "next";
import "./globals.css";
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
      </body>
    </html>
  );
}
