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
              colorBackground: "#07070f",
              colorText: "#e8e8f4",
              colorInputBackground: "#16162a",
              colorInputText: "#e8e8f4",
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
