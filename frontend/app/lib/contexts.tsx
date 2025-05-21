'use client'

import React, { createContext, useState, useContext, ReactNode, useEffect, useRef } from 'react'
import { apiUrls, getApiKey } from './api'
import { debugLog, logFileSelection } from './debug'
import { useAuth } from './auth-context'
import { fetchWithAuth } from './fetch-with-auth'

export interface StoredFile {
  filename: string
  type: string
  is_structured: boolean
}

interface FileContextType {
  files: StoredFile[]
  activeFile: string | null
  setActiveFile: (filename: string | null) => void
  fetchFiles: () => Promise<void>
  deleteFile: (filename: string) => Promise<boolean>
  isLoading: boolean
}

const FileContext = createContext<FileContextType | undefined>(undefined)

export function FileProvider({ children }: { children: ReactNode }) {
  const [files, setFiles] = useState<StoredFile[]>([])
  const [activeFile, setActiveFile] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const isManualSelection = useRef<boolean>(false)
  const initialLoadComplete = useRef<boolean>(false)
  // Keep track of all files to ensure proper selection is maintained
  const previousFiles = useRef<StoredFile[]>([]);
  const { isAuthenticated } = useAuth()

  const fetchFiles = async () => {
    // Don't try to fetch files if not authenticated
    if (!isAuthenticated) {
      setFiles([])
      setActiveFile(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const apiKey = getApiKey()
      const response = await fetchWithAuth(apiUrls.filesList, {
        method: 'GET',
        headers: {
          'X-API-KEY': apiKey,
        },
      })

      if (response.ok) {
        const data = await response.json()
        const newFiles = data.files || []
        
        // Detect if files list has changed to avoid unnecessary re-renders
        const hasFilesChanged = JSON.stringify(newFiles) !== JSON.stringify(previousFiles.current);
        if (!hasFilesChanged && previousFiles.current.length > 0) {
          // If files haven't changed, just update the state silently
          setIsLoading(false);
          return;
        }
        
        // Update our files state
        setFiles(newFiles)
        previousFiles.current = newFiles;
        
        debugLog('Files updated:', newFiles);
        debugLog('Current active file:', activeFile);
        debugLog('User manually selected?', isManualSelection.current);
        
        // If there's only one file, always select it automatically
        if (newFiles.length === 1 && (!activeFile || activeFile !== newFiles[0].filename)) {
          const onlyFile = newFiles[0].filename;
          logFileSelection(onlyFile, 'auto-select-only-file');
          setActiveFile(onlyFile);
          // Don't mark as manual selection so it can be overridden if more files are added
          isManualSelection.current = false;
        }
        // Only set default file on initial load when there are no selections yet
        else if (!initialLoadComplete.current && newFiles.length > 0 && !activeFile) {
          // First time loading, auto-select first file
          const firstFile = newFiles[0].filename;
          logFileSelection(firstFile, 'initial-load');
          setActiveFile(firstFile);
          initialLoadComplete.current = true;
        }
        // If we had a manually selected file, verify it still exists
        else if (activeFile && isManualSelection.current) {
          const fileStillExists = newFiles.some((file: StoredFile) => file.filename === activeFile);
          if (!fileStillExists) {
            // File was deleted, pick a new one
            if (newFiles.length > 0) {
              const newActiveFile = newFiles[0].filename;
              logFileSelection(newActiveFile, 'selected-file-deleted');
              setActiveFile(newActiveFile);
              isManualSelection.current = false;
            } else {
              // No files left
              logFileSelection(null, 'no-files-left');
              setActiveFile(null);
            }
          }
          // If the file still exists, keep it selected
        }
        // If we had an auto-selected file but never manually selected
        else if (activeFile && !isManualSelection.current && newFiles.length > 0) {
          // Check if file still exists
          const fileStillExists = newFiles.some((file: StoredFile) => file.filename === activeFile);
          if (!fileStillExists) {
            // Select new first file
            const newActiveFile = newFiles[0].filename;
            logFileSelection(newActiveFile, 'auto-selected-file-deleted');
            setActiveFile(newActiveFile);
          }
        }
        // Handle the case where there are no files
        else if (newFiles.length === 0) {
          logFileSelection(null, 'empty-files-list');
          setActiveFile(null);
        }
      }
    } catch (error) {
      console.error('Error fetching files:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Custom setActiveFile function that tracks if the selection was manual
  const handleSetActiveFile = (filename: string | null) => {
    logFileSelection(filename, 'user-selection');
    isManualSelection.current = true;
    setActiveFile(filename);
  }

  const deleteFile = async (filename: string): Promise<boolean> => {
    if (!isAuthenticated) return false;
    
    try {
      const apiKey = getApiKey()
      const response = await fetchWithAuth(apiUrls.fileDelete(filename), {
        method: 'DELETE',
        headers: {
          'X-API-KEY': apiKey,
        },
      })

      if (response.ok) {
        // Update local state immediately for better UX
        const remainingFiles = files.filter(file => file.filename !== filename)
        setFiles(remainingFiles)
        previousFiles.current = remainingFiles;
        
        // If deleted file was active, select a new one
        if (activeFile === filename) {
          if (remainingFiles.length > 0) {
            const newActiveFile = remainingFiles[0].filename;
            logFileSelection(newActiveFile, 'deleted-active-file');
            setActiveFile(newActiveFile);
            isManualSelection.current = false;
          } else {
            logFileSelection(null, 'deleted-last-file');
            setActiveFile(null);
          }
        }
        
        return true
      }
      return false
    } catch (error) {
      console.error('Delete error:', error)
      return false
    }
  }

  useEffect(() => {
    // Don't set up polling if not authenticated
    if (!isAuthenticated) {
      setFiles([])
      setActiveFile(null)
      setIsLoading(false)
      return () => {}
    }
    
    // Initial fetch
    fetchFiles()
    
    // Set up polling for refreshing files list
    const interval = setInterval(fetchFiles, 5000)
    return () => clearInterval(interval)
  }, [isAuthenticated]) // Re-run effect when authentication state changes

  return (
    <FileContext.Provider value={{ 
      files, 
      activeFile, 
      setActiveFile: handleSetActiveFile, 
      fetchFiles, 
      deleteFile, 
      isLoading 
    }}>
      {children}
    </FileContext.Provider>
  )
}

export function useFiles() {
  const context = useContext(FileContext)
  if (context === undefined) {
    throw new Error('useFiles must be used within a FileProvider')
  }
  return context
} 