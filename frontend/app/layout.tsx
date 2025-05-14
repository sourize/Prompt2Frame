import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Prompt2Frame',
  description: 'Create animations from text prompts!',
  icons: {
    icon: '/favicon.ico',
  },
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
