import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'MandateTrail · Orbital Intelligence', description: 'Financial agent integrity and runtime security · synthetic sandbox' };
export default function RootLayout({ children }: Readonly<{children:React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
