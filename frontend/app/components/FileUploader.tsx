'use client'
import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { CloudArrowUpIcon, DocumentIcon, CheckCircleIcon, XCircleIcon, TrashIcon } from '@heroicons/react/24/outline'
import { DocumentTextIcon, DocumentChartBarIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { BorderBeam } from './ui/border-beam'
import { apiUrls, getApiKey } from '../lib/api'
import { useFiles } from '../lib/contexts'

interface UploadedFile {
  name: string
  status: 'uploading' | 'success' | 'error'
  error?: string
  progress?: number
}

export interface StoredFile {
  filename: string
  type: string
  is_structured: boolean
}

interface FileUploaderProps {
  onFileUploaded?: () => void
}

export default function FileUploader({ onFileUploaded }: FileUploaderProps = {}) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [deletingFiles, setDeletingFiles] = useState<string[]>([])
  const { files, activeFile, setActiveFile, fetchFiles, deleteFile } = useFiles()

  const clearSuccessfulUploads = () => {
    setUploadedFiles(prev => prev.filter(file => file.status !== 'success'))
  }

  const handleDeleteFile = async (e: React.MouseEvent, filename: string) => {
    e.stopPropagation() // Prevent selecting the file when clicking delete
    
    // Show loading state
    setDeletingFiles(prev => [...prev, filename])
    
    try {
      const success = await deleteFile(filename)
      if (success) {
        // File deletion handled by the context
        // Force refresh files
        setTimeout(() => {
          fetchFiles()
        }, 300)
      }
    } finally {
      // Remove loading state
      setDeletingFiles(prev => prev.filter(f => f !== filename))
    }
  }

  const simulateProgress = (fileName: string) => {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 10
      if (progress > 95) {
        progress = 95 // Cap at 95% until actual completion
        clearInterval(interval)
      }
      
      setUploadedFiles(prevFiles => 
        prevFiles.map(file => 
          file.name === fileName && file.status === 'uploading' 
            ? { ...file, progress: Math.min(Math.round(progress), 95) } 
            : file
        )
      )
    }, 300)

    return interval
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (isUploading) return

    setIsUploading(true)
    const newFiles = acceptedFiles.map(file => ({
      name: file.name,
      status: 'uploading' as const,
      progress: 0
    }))
    
    setUploadedFiles(prev => [...prev, ...newFiles])

    // Start simulated progress for each file
    const intervals = newFiles.map(file => simulateProgress(file.name))

    const formData = new FormData()
    acceptedFiles.forEach(file => {
      formData.append('files', file)
    })

    const apiKey = getApiKey()

    try {
      const response = await fetch(apiUrls.fileUpload, {
        method: 'POST',
        headers: {
          'X-API-KEY': apiKey,
        },
        body: formData,
      })

      // Clear progress intervals
      intervals.forEach(clearInterval)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Upload error response:', errorText)
        throw new Error(`Upload failed: ${response.status} ${errorText}`)
      }

      const data = await response.json()
      
      // Update status for successfully processed files
      setUploadedFiles(prev => prev.map(file => {
        if (data.processed_files?.includes(file.name)) {
          return { ...file, status: 'success' as const, progress: 100 }
        }
        if (data.errors?.find((e: any) => e.filename === file.name)) {
          const error = data.errors.find((e: any) => e.filename === file.name)
          return { ...file, status: 'error' as const, error: error.error, progress: 100 }
        }
        return file
      }))

      // Refresh files in context
      fetchFiles()
      
      // Auto-clear successful uploads after 5 seconds
      setTimeout(clearSuccessfulUploads, 5000)
      
      // Notify parent component about successful upload
      if (onFileUploaded && data.processed_files?.length > 0) {
        onFileUploaded()
      }
    } catch (error) {
      console.error('Upload error:', error)
      // Clear progress intervals
      intervals.forEach(clearInterval)
      // Mark all uploading files as failed
      setUploadedFiles(prev => prev.map(file => 
        file.status === 'uploading' 
          ? { ...file, status: 'error' as const, error: 'Upload failed', progress: 100 }
          : file
      ))
    } finally {
      setIsUploading(false)
    }
  }, [isUploading, fetchFiles, onFileUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
  })

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <div className="h-5 w-5 text-blue-500 dark:text-blue-400 animate-pulse rounded-full bg-blue-100 dark:bg-blue-900/50"></div>
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500 dark:text-green-400" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-500 dark:text-red-400" />
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
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

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="relative bg-white dark:bg-gray-950 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 h-full flex flex-col transition-colors duration-200 w-full overflow-hidden"
    >
      <BorderBeam
        size={80}
        duration={10}
        colorFrom="#34D399" 
        colorTo="#3B82F6"
      />
      
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-lg font-medium text-gray-800 dark:text-gray-100 flex items-center">
          <CloudArrowUpIcon className="h-5 w-5 mr-2 text-blue-600 dark:text-blue-400" />
          Document Manager
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Upload new files or select existing documents
        </p>
      </div>
      
      <div className="p-4 flex-1 overflow-auto flex flex-col">
        {/* File Selector Section */}
        {files.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
              Available Documents
              <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 font-normal">
                (Select a file to chat with)
              </span>
            </h3>
            <div className="bg-white dark:bg-gray-950 rounded-md p-2 shadow-sm mb-2 border border-gray-200 dark:border-gray-800">
              <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                {files.map((file) => (
                  <motion.div
                    key={file.filename}
                    whileHover={{ scale: 1.01 }}
                    onClick={() => {
                      console.log("User selected file:", file.filename);
                      setActiveFile(file.filename);
                    }}
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
          </div>
        )}

        {/* Upload section */}
        <>
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
              Upload New Files
            </h3>
            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors mb-4 ${
                isDragActive 
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                  : 'border-gray-300 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500'
              }`}
            >
              <input {...getInputProps()} />
              <CloudArrowUpIcon className={`h-10 w-10 mx-auto mb-2 ${
                isDragActive 
                  ? 'text-blue-500 dark:text-blue-400' 
                  : 'text-gray-400 dark:text-gray-500'
              }`} />
              {isDragActive ? (
                <p className="text-blue-500 dark:text-blue-400 font-medium">Drop the files here...</p>
              ) : (
                <div>
                  <p className="text-gray-600 dark:text-gray-300">Drag & drop files here, or click to select files</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Supported: PDF, DOCX, PPTX, TXT, MD, CSV, XLSX, XLS
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Current Upload Status */}
          {uploadedFiles.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
                Current Uploads
              </h3>
              <div className="space-y-2">
                {uploadedFiles.map((file, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                    className="flex items-center p-2 bg-white dark:bg-gray-950 rounded-md border border-gray-200 dark:border-gray-800"
                  >
                    <div className="mr-2">{getStatusIcon(file.status)}</div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <span className="truncate text-sm font-medium text-gray-700 dark:text-gray-300">{file.name}</span>
                      </div>
                      
                      {file.status === 'uploading' && file.progress !== undefined && (
                        <div className="w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden mt-1">
                          <div 
                            className="h-full bg-blue-500 dark:bg-blue-600 rounded-full" 
                            style={{ width: `${file.progress}%` }}
                          ></div>
                        </div>
                      )}
                      
                      {file.error && (
                        <span className="text-xs text-red-500 dark:text-red-400">{file.error}</span>
                      )}
                    </div>
                    
                    {file.status === 'success' && (
                      <span className="text-xs text-green-600 dark:text-green-400 ml-2">Complete</span>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Complete Message */}
          {!isUploading && uploadedFiles.some(file => file.status === 'success') && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
              <p className="text-green-700 dark:text-green-400 text-sm">
                Files uploaded successfully! Select a file above to start chatting.
              </p>
            </div>
          )}
        </>
      </div>
    </motion.div>
  )
}
