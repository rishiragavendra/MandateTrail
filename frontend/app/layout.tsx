import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '../components/theme-provider';
export const metadata: Metadata = { title: 'MandateTrail · Orbital Intelligence', description: 'Financial agent integrity and runtime security · synthetic sandbox' };
const themeBootstrap = `(function(){try{document.documentElement.dataset.theme=localStorage.getItem('mandatetrail-theme')==='light'?'light':'dark'}catch(e){document.documentElement.dataset.theme='dark'}})();`;
export default function RootLayout({ children }: Readonly<{children:React.ReactNode}>) {
  return <html lang="en" data-theme="dark" suppressHydrationWarning>
    <head><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
    <body><ThemeProvider>{children}</ThemeProvider></body>
  </html>;
}
