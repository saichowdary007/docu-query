'use client'
import React, { useState, useEffect } from 'react'
import FileUploader from './components/FileUploader'
import ChatInterface from './components/ChatInterface'
import AppLayout from './components/AppLayout'
import { motion } from 'framer-motion'

export default function Home() {
  const [fileCount, setFileCount] = useState(0)
  const [mounted, setMounted] = useState(false)
  
  // Fetch file count to adjust layout
  useEffect(() => {
    // Mark component as mounted
    setMounted(true)
    
    const fetchFileCount = async () => {
      try {
        const apiKey = process.env.NEXT_PUBLIC_BACKEND_API_KEY || 'secret_api_key_123'
        const response = await fetch('http://localhost:8000/api/v1/files/uploaded-files', {
          method: 'GET',
          headers: {
            'X-API-KEY': apiKey,
          },
        })

        if (response.ok) {
          const data = await response.json()
          setFileCount(data.files?.length || 0)
        }
      } catch (error) {
        console.error('Error fetching file count:', error)
      }
    }

    fetchFileCount()
    // Poll for changes every 5 seconds
    const interval = setInterval(fetchFileCount, 5000)
    return () => clearInterval(interval)
  }, [])

  // Default layout for server rendering to prevent hydration mismatch
  let chatWidth = 'w-full md:w-2/3 lg:w-3/4'
  let fileUploaderWidth = 'w-full md:w-1/3 lg:w-1/4'

  // Adjust layout based on file count only after mounting to avoid hydration errors
  if (mounted) {
    // If very few files, give more space to chat interface
    chatWidth = fileCount <= 2 
      ? 'w-full md:w-3/4 lg:w-4/5' 
      : 'w-full md:w-2/3 lg:w-3/4'

    fileUploaderWidth = fileCount <= 2
      ? 'w-full md:w-1/4 lg:w-1/5'
      : 'w-full md:w-1/3 lg:w-1/4'
  }

  return (
    <AppLayout>
      <div className="flex flex-col md:flex-row w-full gap-4 px-2 py-4 h-full">
        <motion.div 
          className={`${fileUploaderWidth} h-full`}
          layout
          transition={{ duration: 0.3 }}
        >
          <FileUploader />
        </motion.div>
        <motion.div 
          className={`${chatWidth} h-full`}
          layout
          transition={{ duration: 0.3 }}
        >
          <ChatInterface />
        </motion.div>
      </div>
    </AppLayout>
  )
}
