'use client'
import React, { useState, useEffect } from 'react'
import { DocumentTextIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { SunIcon, MoonIcon } from '@heroicons/react/24/solid'
import { useTheme } from 'next-themes'
import { motion } from 'framer-motion'
import { BorderBeam } from './ui/border-beam'

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [mounted, setMounted] = useState(false)
  const { resolvedTheme, setTheme } = useTheme()

  useEffect(() => {
    setMounted(true)
    return () => {}
  }, [])

  // Function to toggle theme
  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
  }

  return (
    <div className="min-h-screen h-screen flex flex-col bg-gray-50 dark:bg-black">
      {/* Header */}
      <header className="relative bg-white dark:bg-gray-950 shadow-sm border-b border-gray-200 dark:border-gray-800 overflow-hidden">
        <BorderBeam 
          size={60}
          duration={12} 
          colorFrom="#3B82F6" 
          colorTo="#8B5CF6"
        />
        <div className="w-full px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <motion.h1 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-2xl font-bold text-gray-900 dark:text-white flex items-center"
              >
                <DocumentTextIcon className="h-8 w-8 mr-2 text-blue-600 dark:text-blue-400" />
                DocuQuery-AI
              </motion.h1>
            </div>
            <div className="flex items-center space-x-2">
              {mounted && (
                <>
                  <motion.button 
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={toggleTheme}
                    className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-900 focus:outline-none"
                    title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                    aria-label="Toggle theme"
                  >
                    {resolvedTheme === 'dark' ? (
                      <SunIcon className="h-5 w-5 text-yellow-400" />
                    ) : (
                      <MoonIcon className="h-5 w-5 text-gray-500" />
                    )}
                  </motion.button>
                  <motion.button 
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-900 focus:outline-none"
                    title="Refresh documents"
                  >
                    <ArrowPathIcon className="h-5 w-5" />
                  </motion.button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-gray-50 dark:bg-black focus:outline-none flex flex-col">
        {children}
      </main>
    </div>
  )
} 