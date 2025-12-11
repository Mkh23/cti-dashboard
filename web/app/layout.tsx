import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CTI Dashboard",
  description: "Ultrasound group grading dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
