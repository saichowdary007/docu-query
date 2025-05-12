import React, { useState, useEffect } from 'react';
import { uploadFile } from '../api';

/**
 * DocumentManager component for handling document uploads and management
 */
const DocumentManager = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Load documents when component mounts
  useEffect(() => {
    // In a future implementation, this would fetch documents from an API
    // For now, we'll just use local state
  }, []);

  /**
   * Handle file selection
   */
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadError(null); // Clear any previous errors
    }
  };

  /**
   * Handle file upload
   */
  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) return;
    
    try {
      setUploading(true);
      setUploadProgress(0);
      setUploadError(null);
      
      // Create an interval to simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 5;
          if (newProgress >= 95) {
            clearInterval(progressInterval);
            return 95;
          }
          return newProgress;
        });
      }, 200);
      
      // Upload the file
      const result = await uploadFile(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Handle successful upload
      if (result && result.success) {
        // Add the document to our list
        const newDoc = {
          id: result.file_id,
          name: file.name,
          type: file.type || result.file_type,
          size: file.size,
          uploaded: new Date().toISOString(),
          chunks_count: result.chunks_count || 0
        };
        
        setDocuments(prev => [...prev, newDoc]);
        
        // Call the onUploadSuccess callback if provided
        if (onUploadSuccess) {
          onUploadSuccess(newDoc);
        }
        
        // Reset file input
        setFile(null);
        
        // Reset progress after a short delay to show completion
        setTimeout(() => {
          setUploadProgress(0);
          setUploading(false);
        }, 700);
      } else {
        throw new Error(result?.message || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadError(error.message || 'Failed to upload file');
      setUploading(false);
      setUploadProgress(0);
    }
  };

  /**
   * Get file type icon
   */
  const getFileIcon = (fileName) => {
    if (!fileName) return '📄';
    
    const ext = fileName.split('.').pop().toLowerCase();
    
    switch (ext) {
      case 'pdf': return '📕';
      case 'docx':
      case 'doc': return '📘';
      case 'xlsx':
      case 'xls':
      case 'csv': return '📊';
      case 'pptx':
      case 'ppt': return '📊';
      case 'txt': return '📝';
      case 'md': return '📑';
      default: return '📄';
    }
  };

  /**
   * Format file size
   */
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-4">
      <h2 className="text-xl font-semibold mb-4">Document Manager</h2>
      
      {/* Upload Form */}
      <form onSubmit={handleUpload} className="mb-6">
        <div className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <input
              type="file"
              id="file-upload"
              onChange={handleFileChange}
              className="hidden"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.pptx,.ppt"
              disabled={uploading}
            />
            <label 
              htmlFor="file-upload" 
              className="cursor-pointer flex flex-col items-center justify-center"
            >
              <svg 
                className="w-12 h-12 text-gray-400 mb-2" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth="2" 
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              {file ? (
                <span className="text-blue-600 font-medium">{file.name} ({formatSize(file.size)})</span>
              ) : (
                <span className="text-gray-500">
                  Click to select a document or drag and drop
                  <p className="text-sm text-gray-400 mt-1">
                    PDF, DOCX, XLSX/XLS, CSV, TXT, MD, PPTX
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    <span className="font-semibold">Note:</span> For older Excel files (.xls), modern Office formats (.xlsx) are recommended for better compatibility
                  </p>
                </span>
              )}
            </label>
          </div>
          
          {uploadProgress > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                style={{ width: `${uploadProgress}%` }} 
              ></div>
            </div>
          )}
          
          {uploadError && (
            <div className="text-red-500 text-sm">
              Error: {uploadError}
            </div>
          )}
          
          <button
            type="submit"
            disabled={!file || uploading}
            className={`w-full py-2 px-4 rounded-md text-white font-medium ${
              !file || uploading 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </form>
      
      {/* Document List */}
      <div>
        <h3 className="text-lg font-medium mb-2">Uploaded Documents</h3>
        
        {documents.length === 0 ? (
          <p className="text-gray-500 text-center py-4">
            No documents uploaded yet
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div 
                key={doc.id} 
                className="flex items-center p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="text-2xl mr-3">
                  {getFileIcon(doc.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {doc.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatSize(doc.size)} • {doc.chunks_count} chunks
                  </p>
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(doc.uploaded).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentManager; 