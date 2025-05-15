'use client'

import { useState, useRef, useEffect } from 'react'
import { useAutoAnimate } from '@formkit/auto-animate/react'
import { PaperAirplaneIcon, ArrowDownTrayIcon, DocumentTextIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { BorderBeam } from './ui/border-beam'
import { apiUrls, getApiKey } from '../lib/api'
import { useFiles } from '../lib/contexts'

interface Message {
  role: 'user' | 'assistant'
  content: string
  type?: 'text' | 'list' | 'table'
  data?: any[]
  columns?: string[]
  download_available?: boolean
  download_filename?: string
  file_context?: string
  query_params_for_download?: any
  sheet_name_for_download?: string
  drop_duplicates_for_download?: boolean
  subset_for_download?: string[]
  return_columns_for_download?: string[] | null
  timestamp?: number
}

// Maximum rows to display in the collapsed view
const MAX_ROWS_COLLAPSED = 10

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your document assistant. Upload files and ask me anything about them.',
      timestamp: Date.now()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mounted, setMounted] = useState(false)
  // Track expanded state for each message by its index
  const [expandedMessages, setExpandedMessages] = useState<Record<number, boolean>>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [parent] = useAutoAnimate()
  const { activeFile, files } = useFiles()
  const prevActiveFileRef = useRef<string | null>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Set mounted state and focus input after sending a message
  useEffect(() => {
    setMounted(true)
    
    if (!isLoading && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isLoading, messages])

  // Update welcome message when active file changes
  useEffect(() => {
    // Only update if the component is mounted and activeFile has actually changed
    if (mounted && prevActiveFileRef.current !== activeFile) {
      prevActiveFileRef.current = activeFile
      
      if (activeFile && files.length > 0) {
        const activeFileObj = files.find(f => f.filename === activeFile)
        const fileTypeText = activeFileObj?.is_structured ? 'structured data file' : 'document'
        
        setMessages([{
          role: 'assistant',
          content: `Hello! I'm ready to answer questions about "${activeFile}". This appears to be a ${fileTypeText}. What would you like to know?`,
          timestamp: Date.now()
        }])
      } else if (files.length > 0 && !activeFile) {
        setMessages([{
          role: 'assistant',
          content: 'Please select a file to chat with from the file manager.',
          timestamp: Date.now()
        }])
      }
    }
  }, [activeFile, files, mounted])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    
    // Check if a file is selected
    if (!activeFile) {
      setMessages(prev => [...prev, {
        role: 'user',
        content: input.trim(),
        timestamp: Date.now()
      }, {
        role: 'assistant',
        content: 'Please select a file to chat with before asking questions.',
        timestamp: Date.now()
      }])
      setInput('')
      return
    }

    const userMessage = input.trim()
    setInput('')
    const userMessageObj: Message = { 
      role: 'user', 
      content: userMessage,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMessageObj])
    setIsLoading(true)

    try {
      const apiKey = getApiKey()
      
      const response = await fetch(apiUrls.chat, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY': apiKey,
        },
        body: JSON.stringify({
          query: userMessage,
          file_context: activeFile
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      console.log("API Response data:", data);  // Log the raw API response data
      console.log("Return columns from API:", data.return_columns_for_download);
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        type: data.type,
        data: data.data,
        columns: data.columns,
        download_available: data.download_available,
        download_filename: data.download_filename,
        file_context: data.file_context,
        query_params_for_download: data.query_params_for_download,
        sheet_name_for_download: data.sheet_name_for_download,
        drop_duplicates_for_download: data.drop_duplicates_for_download,
        subset_for_download: data.subset_for_download,
        return_columns_for_download: data.return_columns_for_download,
        timestamp: Date.now()
      }])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: Date.now()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownload = async (message: Message) => {
    if (!message.download_available || !message.download_filename) return

    try {
      const apiKey = getApiKey()
      
      // Log the message object to see what's available
      console.log("Download message data:", message);
      
      // Create a clean request body with default values where needed
      const requestBody = {
        filename_to_download: message.download_filename,
        original_filename: message.file_context,
        query_params: message.query_params_for_download || [], // Default to empty array if undefined
        sheet_name: message.sheet_name_for_download,
        drop_duplicates: message.drop_duplicates_for_download || false,
        subset: message.subset_for_download || null,
        return_columns: message.return_columns_for_download || null
      };
      
      // Log the actual request data
      console.log("Sending download request:", requestBody);
      
      const response = await fetch(apiUrls.fileDownload, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY': apiKey,
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Download API error:', errorText);
        throw new Error('Download failed: ' + errorText);
      }

      // Create a blob from the response
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = message.download_filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: any) {
      console.error('Download error:', error)
      alert('Failed to download file: ' + error.message)
    }
  }

  // Format timestamp to readable time
  const formatTime = (timestamp?: number) => {
    if (!timestamp || !mounted) return ''
    
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Toggle expanded state for a specific message
  const toggleExpanded = (index: number) => {
    setExpandedMessages(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  const renderMessage = (message: Message, index: number) => {
    // Check if this is a large table that should be collapsed
    const isLargeTable = message.type === 'table' && message.data && message.data.length > MAX_ROWS_COLLAPSED
    
    // Get expanded state for this message
    const isExpanded = expandedMessages[index] || false
    
    // Calculate how many rows to display based on expanded state
    const visibleRows = message.data
      ? (isLargeTable && !isExpanded
          ? message.data.slice(0, MAX_ROWS_COLLAPSED)
          : message.data)
      : []
        
    if (message.role === 'user') {
      return (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex justify-end mb-4"
        >
          <div className="bg-blue-600 text-white py-3 px-4 rounded-2xl rounded-tr-none max-w-[80%] shadow-sm">
            <p>{message.content}</p>
            <div className="text-xs text-blue-100 text-right mt-1">
              {formatTime(message.timestamp)}
            </div>
          </div>
        </motion.div>
      )
    }

    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="flex mb-4"
      >
        <div className="bg-white dark:bg-gray-950 py-3 px-4 rounded-2xl rounded-tl-none max-w-[80%] shadow-sm border border-gray-100 dark:border-gray-800">
          <p className="text-gray-800 dark:text-gray-100 mb-2">{message.content}</p>
          
          {message.type === 'list' && message.data && (
            <ul className="list-disc pl-5 space-y-1 mb-2 text-gray-700 dark:text-gray-300">
              {message.data.map((item, index) => (
                <li key={index}>{String(item)}</li>
              ))}
            </ul>
          )}

          {message.type === 'table' && message.data && message.columns && (
            <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700 mb-2">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    {message.columns.map((column, colIndex) => (
                      <th
                        key={colIndex}
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {visibleRows.map((row, rowIndex) => (
                    <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-900'}>
                      {message.columns && message.columns.map((column, colIndex) => (
                        <td
                          key={`${rowIndex}-${colIndex}`}
                          className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
                        >
                          {row[column]?.toString() || ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {isLargeTable && message.data && (
                <div className="flex justify-center py-2 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
                  <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => toggleExpanded(index)}
                    className="flex items-center px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUpIcon className="h-4 w-4 mr-1" />
                        Show Less ({message.data.length} total rows)
                      </>
                    ) : (
                      <>
                        <ChevronDownIcon className="h-4 w-4 mr-1" />
                        Show More ({message.data.length - MAX_ROWS_COLLAPSED} more rows)
                      </>
                    )}
                  </motion.button>
                </div>
              )}
            </div>
          )}

          {message.download_available && (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleDownload(message)}
              className="flex items-center mt-2 px-3 py-1.5 text-sm bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
              Download Results
            </motion.button>
          )}
          
          <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="relative bg-gray-50 dark:bg-black rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col w-full h-full overflow-hidden"
    >
      <BorderBeam 
        size={100}
        duration={8} 
        colorFrom="#4F46E5" 
        colorTo="#8B5CF6"
      />
      
      {/* Chat Header */}
      <div className="bg-white dark:bg-gray-950 px-4 py-3 border-b border-gray-200 dark:border-gray-800 rounded-t-lg">
        <h2 className="text-lg font-medium text-gray-800 dark:text-gray-100 flex items-center">
          <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600 dark:text-blue-400" />
          Chat with your documents
        </h2>
        
        {activeFile ? (
          <div className="mt-1 flex items-center">
            <span className="px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 text-sm font-medium border border-blue-200 dark:border-blue-800">
              Currently querying: <span className="font-bold">{activeFile}</span>
            </span>
          </div>
        ) : (
          <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
            Please select a file from the file manager to start chatting
          </p>
        )}
      </div>

      {/* Messages Container */}
      <div 
        ref={parent}
        className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-100 dark:bg-black"
      >
        {messages.map((message, index) => (
          <div key={index}>
            {renderMessage(message, index)}
          </div>
        ))}
        
        {isLoading && (
          <div className="flex mb-4">
            <div className="bg-white dark:bg-gray-950 py-3 px-4 rounded-2xl rounded-tl-none max-w-xs shadow-sm border border-gray-100 dark:border-gray-800">
              <div className="flex space-x-2">
                <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-700 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-700 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-700 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-4 rounded-b-lg">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={activeFile ? "Ask a question about this document..." : "Please select a file first"}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading || !activeFile}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            disabled={isLoading || !input.trim() || !activeFile}
            className={`p-2 rounded-full ${
              isLoading || !input.trim() || !activeFile
                ? 'bg-gray-200 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700 dark:hover:bg-blue-500'
            } focus:outline-none transition-colors`}
          >
            <PaperAirplaneIcon className="h-5 w-5" />
          </motion.button>
        </form>
      </div>
    </motion.div>
  )
}
