'use client'
import React, { useState, useEffect, useRef } from 'react'
import { DocumentTextIcon, ArrowPathIcon, UserCircleIcon } from '@heroicons/react/24/outline'
import { SunIcon, MoonIcon } from '@heroicons/react/24/solid'
import { useTheme } from 'next-themes'
import { motion, AnimatePresence } from 'framer-motion'
import { BorderBeam } from './ui/border-beam'
import { useAuth } from '@/app/lib/auth-context'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [mounted, setMounted] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const { resolvedTheme, setTheme } = useTheme()
  const { user, isAuthenticated, isLoading, logout } = useAuth()
  const router = useRouter()
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    setMounted(true)
    return () => {}
  }, [])

  // Client-side authentication check to redirect when not authenticated
  useEffect(() => {
    // Only redirect after initial loading is complete and we're sure user isn't authenticated
    if (mounted && !isLoading && !isAuthenticated) {
      // Don't redirect if we're already on a public route
      const publicRoutes = ['/login', '/register']
      const pathname = window.location.pathname
      
      if (!publicRoutes.includes(pathname)) {
        console.log('Not authenticated, redirecting to login page')
        router.push('/login')
      }
    }
  }, [mounted, isLoading, isAuthenticated, router])

  // Handle click outside dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownOpen &&
        dropdownRef.current && 
        buttonRef.current && 
        !dropdownRef.current.contains(event.target as Node) && 
        !buttonRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }

    // Handle escape key press
    function handleEscKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && dropdownOpen) {
        setDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscKey)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscKey)
    }
  }, [dropdownOpen])

  // Function to toggle theme
  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
  }
  
  // Function to handle logout
  const handleLogout = () => {
    logout()
    setDropdownOpen(false)
    router.push('/login')
  }

  // Show loading state or only authenticated content
  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen h-screen flex flex-col bg-gray-50 dark:bg-black">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 w-full bg-white dark:bg-gray-950 shadow-sm border-b border-gray-200 dark:border-gray-800 z-[2000]">
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
                  
                  {/* User profile section */}
                  <div className="relative ml-3" style={{ zIndex: 9999 }}>
                    {isAuthenticated ? (
                      <>
                        <motion.button
                          ref={buttonRef}
                          onClick={() => setDropdownOpen(!dropdownOpen)}
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className="flex items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800 focus:outline-none"
                          aria-expanded={dropdownOpen}
                          aria-haspopup="true"
                        >
                          {user?.profile_picture ? (
                            <img 
                              src={user.profile_picture} 
                              alt={user.full_name || user.email}
                              className="h-8 w-8 rounded-full object-cover"
                            />
                          ) : (
                            <div className="h-8 w-8 rounded-full flex items-center justify-center bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300">
                              <span className="text-sm font-medium">
                                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : user?.email.charAt(0).toUpperCase()}
                              </span>
                            </div>
                          )}
                        </motion.button>
                        
                        <AnimatePresence>
                          {dropdownOpen && (
                            <>
                              {/* Overlay to prevent clicks passing through */}
                              <div 
                                className="fixed inset-0" 
                                style={{ zIndex: 9990 }}
                                onClick={() => setDropdownOpen(false)} 
                              />
                              
                              <motion.div
                                ref={dropdownRef}
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ duration: 0.2 }}
                                style={{
                                  position: 'absolute',
                                  top: 'calc(100% + 8px)',
                                  right: 0,
                                  width: '12rem',
                                  zIndex: 99999,
                                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
                                }}
                                className="py-2 bg-white dark:bg-gray-900 rounded-md border border-gray-200 dark:border-gray-700"
                              >
                                <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {user?.full_name || 'User'}
                                  </p>
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {user?.email}
                                  </p>
                                </div>
                                
                                <div className="py-1">
                                  <button
                                    onClick={handleLogout}
                                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                                  >
                                    Sign out
                                  </button>
                                </div>
                              </motion.div>
                            </>
                          )}
                        </AnimatePresence>
                      </>
                    ) : (
                      <Link href="/login">
                        <motion.div
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          <UserCircleIcon className="h-5 w-5" />
                          <span className="text-sm font-medium">Sign in</span>
                        </motion.div>
                      </Link>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Add padding-top to accommodate fixed header */}
      <main className="flex-1 overflow-y-auto bg-gray-50 dark:bg-black focus:outline-none flex flex-col pt-[76px]">
        {children}
      </main>
    </div>
  )
}
