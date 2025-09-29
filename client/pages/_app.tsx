// client/_app.tsx
import type { AppProps } from 'next/app'
import '@/styles/globals.css'
import { Inter, JetBrains_Mono } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <main className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
      <Component {...pageProps} />
    </main>
  )
}
