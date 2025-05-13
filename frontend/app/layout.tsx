import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Text-to-Animation (Miaim)',
  description: 'Create animations from text prompts!',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
