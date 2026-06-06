import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tradeo',
  description: 'Private automated pattern research dashboard'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  )
}
