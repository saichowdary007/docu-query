import './styles/globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ThemeProvider } from "@/app/theme-provider"
import { FileProvider } from "@/app/lib/contexts"
import { AuthProvider } from "@/app/lib/auth-context"

const inter = Inter({ 
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

export const metadata: Metadata = {
  title: 'DocuQuery AI',
  description: 'Intelligent document query system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className={`${inter.className} dark:bg-black`} suppressHydrationWarning>
        <ThemeProvider>
          <AuthProvider>
            <FileProvider>
              {children}
            </FileProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
} 