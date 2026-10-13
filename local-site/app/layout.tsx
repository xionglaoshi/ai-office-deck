import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "我的AI办公台",
  description: "待办事项、应关注事项与近期工作记录。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
