'use client'

import { useState } from 'react'
import { DocumentTextIcon, DocumentIcon, DocumentChartBarIcon, TrashIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { useFiles } from '../lib/contexts'

export default function FileSelector() {
  const { files, activeFile, setActiveFile, deleteFile, isLoading, fetchFiles } = useFiles()
  const [deletingFiles, setDeletingFiles] = useState<string[]>([])

  const handleDeleteFile = async (e: React.MouseEvent, filename: string) => {
    e.stopPropagation() // Prevent selecting the file when clicking delete
    
    // Show loading state
    setDeletingFiles(prev => [...prev, filename])
    
    try {
      const success = await deleteFile(filename)
      if (success) {
        // Deletion handled by the context
        // Force refresh files after a short delay to ensure backend processing is complete
        setTimeout(() => {
          fetchFiles()
        }, 300)
      }
    } finally {
      // Remove loading state
      setDeletingFiles(prev => prev.filter(f => f !== filename))
    }
  }

  const getFileIcon = (type: string, isStructured: boolean = false) => {
    if (isStructured) {
      return <DocumentChartBarIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
    }
    
    switch (type.toLowerCase()) {
      case 'pdf':
        return <DocumentTextIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
      case 'docx':
      case 'doc':
        return <DocumentTextIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
      case 'xls':
      case 'xlsx':
      case 'csv':
        return <DocumentChartBarIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
      case 'txt':
      case 'md':
        return <DocumentIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  if (isLoading && files.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-950 rounded-md p-2 shadow-sm mb-2">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Loading files...</span>
        </div>
        <div className="mt-2 space-y-2">
          {[1, 2].map(i => (
            <div key={i} className="flex items-center p-2 rounded-md animate-pulse">
              <div className="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 mr-2"></div>
              <div className="flex-1 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-950 rounded-md p-2 shadow-sm mb-2">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">No files available</span>
        </div>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center py-2">
          Upload files to get started
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-950 rounded-md p-2 shadow-sm mb-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-800 dark:text-gray-200">Select a file to chat with:</span>
      </div>
      <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
        {files.map((file) => (
          <motion.div
            key={file.filename}
            whileHover={{ scale: 1.01 }}
            onClick={() => setActiveFile(file.filename)}
            className={`flex items-center p-2 rounded-md cursor-pointer ${
              activeFile === file.filename
                ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                : 'hover:bg-gray-50 dark:hover:bg-gray-900 border border-transparent'
            }`}
          >
            <div className="mr-2">{getFileIcon(file.type, file.is_structured)}</div>
            <div className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
              {file.filename}
            </div>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => handleDeleteFile(e, file.filename)}
              disabled={deletingFiles.includes(file.filename)}
              className={`ml-2 p-1 rounded-full ${
                deletingFiles.includes(file.filename)
                  ? 'opacity-50 cursor-not-allowed'
                  : 'text-gray-400 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              title="Delete file"
            >
              {deletingFiles.includes(file.filename) ? (
                <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-700 border-t-transparent animate-spin"></div>
              ) : (
                <TrashIcon className="h-5 w-5" />
              )}
            </motion.button>
          </motion.div>
        ))}
      </div>
    </div>
  )
} 