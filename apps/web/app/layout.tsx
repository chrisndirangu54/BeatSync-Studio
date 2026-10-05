import "./globals.css";
import AuthGate from "@/components/AuthGate";

export const metadata = {
  title: "BeatSync Studio",
  description: "AI music-video direction powered by Intelligent Beat Sync"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body><AuthGate>{children}</AuthGate></body>
    </html>
  );
}
