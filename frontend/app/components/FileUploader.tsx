'use client'
import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { CloudArrowUpIcon, DocumentIcon, CheckCircleIcon, XCircleIcon, TrashIcon } from '@heroicons/react/24/outline'
import { DocumentTextIcon, DocumentChartBarIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'

interface UploadedFile {
  name: string
  status: 'uploading' | 'success' | 'error'
  error?: string
  progress?: number
}

interface StoredFile {
  filename: string
  type: string
  is_structured: boolean
}

export default function FileUploader() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [storedFiles, setStoredFiles] = useState<StoredFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  // Fetch stored files on component mount and after uploads
  const fetchStoredFiles = async () => {
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
        setStoredFiles(data.files || [])
      }
    } catch (error) {
      console.error('Error fetching stored files:', error)
    }
  }

  useEffect(() => {
    fetchStoredFiles()
    // Set up polling to refresh file list every 30 seconds
    const interval = setInterval(fetchStoredFiles, 30000)
    return () => clearInterval(interval)
  }, [])

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

    const apiKey = process.env.NEXT_PUBLIC_BACKEND_API_KEY || 'secret_api_key_123'
    console.log('Using API Key:', apiKey ? 'API key is set' : 'API key is NOT set')

    try {
      // Use correct URL that works from the browser
      const response = await fetch('http://localhost:8000/api/v1/files/upload', {
        method: 'POST',
        headers: {
          'X-API-KEY': apiKey,
        },
        body: formData,
      })

      console.log('Upload response status:', response.status)
      
      // Clear progress intervals
      intervals.forEach(clearInterval)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Upload error response:', errorText)
        throw new Error(`Upload failed: ${response.status} ${errorText}`)
      }

      const data = await response.json()
      console.log('Upload success response:', data)
      
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

      // Refresh stored files list after successful upload
      await fetchStoredFiles()
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
  }, [isUploading])

  const handleDeleteFile = async (filename: string) => {
    if (isDeleting) return
    
    setIsDeleting(true)
    const apiKey = process.env.NEXT_PUBLIC_BACKEND_API_KEY || 'secret_api_key_123'
    
    try {
      const response = await fetch(`http://localhost:8000/api/v1/files/delete/${filename}`, {
        method: 'DELETE',
        headers: {
          'X-API-KEY': apiKey,
        },
      })

      if (response.ok) {
        // Remove file from the stored files list
        setStoredFiles(prev => prev.filter(file => file.filename !== filename))
        
        // Also remove from upload history if present
        setUploadedFiles(prev => prev.filter(file => file.name !== filename))
      } else {
        console.error('Error deleting file:', await response.text())
      }
    } catch (error) {
      console.error('Delete error:', error)
    } finally {
      setIsDeleting(false)
    }
  }

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

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-white dark:bg-gray-950 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 h-full flex flex-col transition-colors duration-200 w-full"
    >
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-lg font-medium text-gray-800 dark:text-gray-100 flex items-center">
          <CloudArrowUpIcon className="h-5 w-5 mr-2 text-blue-600 dark:text-blue-400" />
          Upload Documents
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Drag & drop or click to upload files
        </p>
      </div>
      
      <div className="p-4 flex-1 overflow-auto flex flex-col">
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

        {/* Current Upload Status */}
        {uploadedFiles.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Recent Uploads</h3>
            <div className="space-y-2 max-h-32 overflow-y-auto rounded-md border border-gray-200 dark:border-gray-800">
              {uploadedFiles.map((file, index) => (
                <motion.div
                  key={`${file.name}-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 * index }}
                  className={`flex items-center p-2 ${
                    index !== uploadedFiles.length - 1 ? 'border-b border-gray-100 dark:border-gray-900' : ''
                  } ${
                    file.status === 'success' ? 'bg-green-50 dark:bg-green-900/20' : 
                    file.status === 'error' ? 'bg-red-50 dark:bg-red-900/20' : 'bg-white dark:bg-gray-950'
                  }`}
                >
                  <span className="mr-2">{getStatusIcon(file.status)}</span>
                  
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

        {/* Stored Files List with Delete Buttons */}
        <div className="flex-1 min-h-0">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Available Files</h3>
          {storedFiles.length === 0 ? (
            <div className="text-center py-8 border border-gray-200 dark:border-gray-800 rounded-md bg-gray-50 dark:bg-black">
              <DocumentIcon className="h-8 w-8 mx-auto text-gray-400 dark:text-gray-500" />
              <p className="text-gray-500 dark:text-gray-400 mt-2">No files available</p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Upload files to get started</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-800 rounded-md divide-y divide-gray-100 dark:divide-gray-900">
              {storedFiles.map((file, index) => (
                <motion.div
                  key={file.filename}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-900"
                >
                  <div className="flex items-center flex-1 min-w-0">
                    <span className="mr-2">{getFileIcon(file.type, file.is_structured)}</span>
                    <span className="truncate text-sm text-gray-700 dark:text-gray-300" title={file.filename}>
                      {file.filename}
                    </span>
                    {file.is_structured && (
                      <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                        Data
                      </span>
                    )}
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => handleDeleteFile(file.filename)}
                    disabled={isDeleting}
                    className="ml-2 p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
                    title="Delete file"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </motion.button>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
