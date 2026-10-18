import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const SITE_URL = 'https://nextsteamgame.com'
const inter = Inter({ subsets: ['latin'], display: 'swap' })

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'Find Similar Steam Games | NextSteamGame',
    template: '%s | NextSteamGame',
  },
  description:
    'Find similar Steam games by mechanics, tags, structure, genre, and music. Start with a game you love and discover what to play next.',
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: 'Find Similar Steam Games | NextSteamGame',
    description:
      'Find similar Steam games by mechanics, tags, structure, genre, and music.',
    url: SITE_URL,
    siteName: 'NextSteamGame',
    type: 'website',
    images: [
      {
        url: '/nextsteamgame-icon.png?v=flared-lamp-6',
        width: 512,
        height: 512,
        alt: 'NextSteamGame',
      },
    ],
  },
  twitter: {
    card: 'summary',
    title: 'Find Similar Steam Games | NextSteamGame',
    description:
      'Find similar Steam games by mechanics, tags, structure, genre, and music.',
    images: ['/nextsteamgame-icon.png'],
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: [
      { url: '/nextsteamgame-icon.svg?v=flared-lamp-6', type: 'image/svg+xml' },
      { url: '/nextsteamgame-icon.png?v=flared-lamp-6', type: 'image/png', sizes: '512x512' },
    ],
    apple: '/apple-touch-icon.png?v=flared-lamp-6',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark bg-background">
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  )
}
