'use client'
import { useState, useEffect } from 'react'
import { 
  DocumentIcon, 
  DocumentTextIcon, 
  DocumentChartBarIcon,
  ClipboardDocumentIcon,
  TrashIcon
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { apiUrls, getApiKey } from '../lib/api'

interface FileInfo {
  filename: string
  type: string
  is_structured: boolean
}

interface FileListProps {
  activeFiles: string[]
  setActiveFiles: (files: string[]) => void
}

export default function FileList({ activeFiles, setActiveFiles }: FileListProps) {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFiles = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const apiKey = getApiKey()
      const response = await fetch(apiUrls.filesList, {
        method: 'GET',
        headers: {
          'X-API-KEY': apiKey,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.status}`)
      }

      const data = await response.json()
      setFiles(data.files || [])
    } catch (err) {
      console.error('Error fetching files:', err)
      setError('Failed to load files')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchFiles()

    // Set up polling to refresh file list every 30 seconds
    const interval = setInterval(fetchFiles, 30000)
    return () => clearInterval(interval)
  }, [])

  const toggleFileSelection = (filename: string) => {
    if (activeFiles.includes(filename)) {
      setActiveFiles(activeFiles.filter(f => f !== filename))
    } else {
      setActiveFiles([...activeFiles, filename])
    }
  }

  const getFileIcon = (type: string, isStructured: boolean) => {
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
        return <ClipboardDocumentIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  const handleDeleteFile = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering the file selection
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return

    try {
      const apiKey = getApiKey()
      const response = await fetch(apiUrls.fileDelete(filename), {
        method: 'DELETE',
        headers: {
          'X-API-KEY': apiKey,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.status}`)
      }

      // Remove from active files if it was selected
      if (activeFiles.includes(filename)) {
        setActiveFiles(activeFiles.filter(f => f !== filename))
      }
      
      // Refresh the file list
      fetchFiles()
    } catch (err) {
      console.error('Error deleting file:', err)
      alert('Failed to delete file')
    }
  }

  if (isLoading && files.length === 0) {
    return (
      <div className="py-4 text-center text-gray-500 dark:text-gray-400">
        <div className="animate-pulse flex justify-center">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
        <div className="animate-pulse flex justify-center mt-2">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
        <div className="mt-2 text-sm">Loading documents...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-4 text-center text-red-500 dark:text-red-400">
        <p>{error}</p>
        <button 
          onClick={fetchFiles}
          className="mt-2 px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="py-4 text-center text-gray-500 dark:text-gray-400">
        <p>No documents uploaded yet.</p>
        <p className="text-sm mt-1">Upload files to get started!</p>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {files.map((file, index) => (
        <motion.li 
          key={file.filename}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: index * 0.05 }}
        >
          <div 
            className={`flex items-center justify-between p-2 rounded-md cursor-pointer ${
              activeFiles.includes(file.filename) 
                ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700' 
                : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
            }`}
            onClick={() => toggleFileSelection(file.filename)}
          >
            <div className="flex items-center min-w-0">
              {getFileIcon(file.type, file.is_structured)}
              <span className={`ml-2 text-sm font-medium truncate ${
                activeFiles.includes(file.filename)
                  ? 'text-blue-700 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300'
              }`} title={file.filename}>
                {file.filename}
              </span>
              {file.is_structured && (
                <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300">
                  Data
                </span>
              )}
            </div>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={(e) => handleDeleteFile(file.filename, e)}
              className="ml-2 p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
              title="Delete file"
            >
              <TrashIcon className="h-4 w-4" />
            </motion.button>
          </div>
        </motion.li>
      ))}
    </ul>
  )
} 