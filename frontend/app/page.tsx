'use client'
import React, { useState, useEffect, useRef } from 'react'
import FileUploader from './components/FileUploader'
import ChatInterface from './components/ChatInterface'
import AppLayout from './components/AppLayout'
import { motion, AnimatePresence } from 'framer-motion'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'
import { apiUrls, getApiKey } from './lib/api'

// RetroGrid component - simplified version from Magic UI
interface RetroGridProps {
  className?: string;
  opacity?: number;
  angle?: number;
  cellSize?: number;
}

const RetroGrid: React.FC<RetroGridProps> = ({ 
  className = "", 
  opacity = 0.2, 
  angle = 65, 
  cellSize = 30 
}) => {
  const gridStyles = {
    '--grid-angle': `${angle}deg`,
    '--cell-size': `${cellSize}px`,
    '--opacity': opacity,
  } as React.CSSProperties;

  return (
    <div
      className={`pointer-events-none absolute size-full overflow-hidden [perspective:200px] opacity-[var(--opacity)] ${className}`}
      style={gridStyles}
    >
      <div className="absolute inset-0 [transform:rotateX(var(--grid-angle))]">
        <div className="animate-grid [background-image:linear-gradient(to_right,var(--light-line,#4338ca)_1px,transparent_0),linear-gradient(to_bottom,var(--light-line,#4338ca)_1px,transparent_0)] [background-repeat:repeat] [background-size:var(--cell-size)_var(--cell-size)] [height:300vh] [inset:0%_0px] [margin-left:-200%] [transform-origin:100%_0_0] [width:600vw] dark:[background-image:linear-gradient(to_right,var(--dark-line,#6366f1)_1px,transparent_0),linear-gradient(to_bottom,var(--dark-line,#6366f1)_1px,transparent_0)]" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-white to-transparent to-90% dark:from-black" />
    </div>
  );
};

export default function Home() {
  const [fileCount, setFileCount] = useState(0)
  const [mounted, setMounted] = useState(false)
  const [isDocManagerExpanded, setIsDocManagerExpanded] = useState(false)
  const lastUploadTime = useRef<number>(0)
  
  // Add keyframes for grid animation
  useEffect(() => {
    const styleSheet = document.styleSheets[0];
    const keyframes = `
      @keyframes grid {
        0% {
          transform: translateY(0px);
        }
        100% {
          transform: translateY(calc(var(--cell-size) * 20));
        }
      }
    `;
    styleSheet.insertRule(keyframes, styleSheet.cssRules.length);
    
    // Define animation class
    const animationStyle = `.animate-grid { animation: grid 20s linear infinite; }`;
    styleSheet.insertRule(animationStyle, styleSheet.cssRules.length);
  }, []);
  
  // Fetch file count to adjust layout
  useEffect(() => {
    // Mark component as mounted
    setMounted(true)
    
    const fetchFileCount = async () => {
      try {
        const apiKey = getApiKey()
        const response = await fetch(apiUrls.filesList, {
          method: 'GET',
          headers: {
            'X-API-KEY': apiKey,
          },
        })

        if (response.ok) {
          const data = await response.json()
          const count = data.files?.length || 0
          
          // If files were just uploaded (timestamp check), auto-close sidebar
          const currentTime = Date.now()
          if (count > fileCount && currentTime - lastUploadTime.current < 5000) {
            setIsDocManagerExpanded(false)
          }
          
          setFileCount(count)
          
          // Only expand sidebar when there are no files and we just mounted
          if (!mounted && count === 0) {
            setIsDocManagerExpanded(true)
          }
        }
      } catch (error) {
        console.error('Error fetching file count:', error)
      }
    }

    fetchFileCount()
    // Poll for changes every 5 seconds
    const interval = setInterval(fetchFileCount, 5000)
    return () => clearInterval(interval)
  }, [mounted, fileCount])

  useEffect(() => {
    // Add an event listener to close the sidebar on mobile when the window is resized
    const handleResize = () => {
      if (window.innerWidth < 768 && isDocManagerExpanded) {
        setIsDocManagerExpanded(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [isDocManagerExpanded])

  // Function to toggle document manager expansion state
  const toggleDocManager = () => {
    setIsDocManagerExpanded(prev => !prev)
  }
  
  // Function to handle file upload - called by FileUploader component
  const handleFileUploaded = () => {
    lastUploadTime.current = Date.now()
  }

  return (
    <AppLayout>
      <div className="h-full flex relative">
        {/* Sidebar with toggle button */}
        <div className="relative z-40">
          {/* Toggle button - positioned to align with header and not interfere with content */}
          <AnimatePresence initial={false}>
            <motion.div 
              key="toggle-button"
              className="fixed top-[76px] z-50"
              initial={{ x: 0 }}
              animate={{ 
                x: isDocManagerExpanded ? 280 - 40 : 16 
              }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
              <button
                onClick={toggleDocManager}
                className="flex items-center justify-center p-2.5 rounded-md bg-white dark:bg-gray-900 shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                aria-label="Toggle document manager"
              >
                <AnimatePresence initial={false} mode="wait">
                  {isDocManagerExpanded ? (
                    <motion.div
                      key="close"
                      initial={{ rotate: -90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      exit={{ rotate: 90, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <XMarkIcon className="h-6 w-6 text-gray-700 dark:text-gray-300" />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="open"
                      initial={{ rotate: 90, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      exit={{ rotate: -90, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Bars3Icon className="h-6 w-6 text-gray-700 dark:text-gray-300" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </button>
            </motion.div>
          </AnimatePresence>
          
          {/* Sidebar panel - align top with toggle button */}
          <div className={`fixed top-[72px] left-0 bottom-0 w-[280px] bg-white dark:bg-gray-950 shadow-xl border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ease-in-out ${
            isDocManagerExpanded ? 'translate-x-0' : '-translate-x-full'
          }`}>
            {/* Top gradient border */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600"></div>
            
            <div className="h-full overflow-auto p-4 pt-14">
              <FileUploader onFileUploaded={handleFileUploaded} />
            </div>
          </div>
        </div>
        
        {/* Overlay for mobile */}
        <AnimatePresence>
          {isDocManagerExpanded && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/50 z-30 md:hidden"
              onClick={() => setIsDocManagerExpanded(false)}
            />
          )}
        </AnimatePresence>
        
        {/* Main content - add padding to accommodate the toggle button */}
        <motion.div 
          className="flex-1"
          animate={{
            marginLeft: isDocManagerExpanded ? '280px' : '0px',
            width: isDocManagerExpanded ? 'calc(100% - 280px)' : '100%'
          }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <div className="h-full p-4 pl-16">
            <ChatInterface />
          </div>
        </motion.div>
      </div>
    </AppLayout>
  )
}
