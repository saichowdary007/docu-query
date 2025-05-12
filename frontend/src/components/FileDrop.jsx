import { useState, useRef } from 'react';
import { uploadFile } from '../api';

const FileDrop = ({ onUploadSuccess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);
  
  // Handle file drop
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files[0]);
    }
  };
  
  // Handle drag events
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };
  
  // Handle file selection
  const handleChange = (e) => {
    e.preventDefault();
    
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files[0]);
    }
  };
  
  // Handle button click
  const handleButtonClick = () => {
    inputRef.current.click();
  };
  
  // Process the selected file
  const handleFiles = (selectedFile) => {
    setFile(selectedFile);
    setError('');
  };
  
  // Handle file upload
  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) return;
    
    setUploading(true);
    setProgress(0);
    setError('');
    
    try {
      // Use an interval to simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return 95;
          }
          return prev + 5;
        });
      }, 100);
      
      const result = await uploadFile(file);
      clearInterval(progressInterval);
      setProgress(100);
      
      if (result && result.success) {
        // Notify parent component of successful upload
        if (onUploadSuccess) {
          onUploadSuccess({
            id: result.file_id,
            name: file.name,
            type: file.type,
            size: file.size,
            file_type: result.file_type,
            chunks_count: result.chunks_count
          });
        }
        
        // Reset form
        setTimeout(() => {
          setFile(null);
          setProgress(0);
          setUploading(false);
        }, 1000);
      } else {
        setError(result?.message || 'Upload failed. Please try again.');
        setProgress(0);
        setUploading(false);
      }
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
      setProgress(0);
      setUploading(false);
    }
  };
  
  // Helper function to format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full h-full flex flex-col">
      <div className="bg-white shadow rounded-lg p-6 flex-grow">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Upload Your Documents
        </h2>
        <p className="text-gray-600 mb-6">
          Upload your documents to get started. You can ask questions about your documents after uploading.
        </p>
        
        <form onSubmit={handleUpload} className="space-y-6 flex-grow">
          {/* File drop zone */}
          <div 
            className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-12
              ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
              ${file ? 'bg-gray-50' : ''}
              transition-colors duration-200`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              ref={inputRef}
              type="file"
              id="file-upload"
              onChange={handleChange}
              className="hidden"
              accept=".pdf,.docx,.xlsx,.csv,.txt,.md,.html,.pptx"
              disabled={uploading}
            />
            
            {!file ? (
              <>
                <svg
                  className="w-12 h-12 text-gray-400 mb-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
                  />
                </svg>
                <p className="mb-2 text-sm text-gray-700">
                  <span className="font-semibold">Click to upload</span> or drag and drop
                </p>
                <p className="text-xs text-gray-500">
                  PDF, DOCX, XLSX, CSV, TXT, MD, HTML, PPTX
                </p>
              </>
            ) : (
              <div className="flex flex-col items-center">
                <div className="text-3xl mb-2">
                  {file.name.endsWith('.pdf') ? '📕' :
                   file.name.endsWith('.docx') ? '📘' :
                   file.name.endsWith('.xlsx') || file.name.endsWith('.csv') ? '📊' :
                   file.name.endsWith('.pptx') ? '📊' : '📄'}
                </div>
                <p className="text-sm font-medium text-gray-900 mb-1">{file.name}</p>
                <p className="text-xs text-gray-500 mb-2">{formatSize(file.size)}</p>
                {!uploading && (
                  <button
                    type="button"
                    onClick={() => setFile(null)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Remove file
                  </button>
                )}
              </div>
            )}
          </div>
          
          {/* Error message */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 p-3 rounded-md">
              {error}
            </div>
          )}
          
          {/* Progress bar */}
          {progress > 0 && (
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>Uploading...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
          
          {/* Action buttons */}
          <div className="flex justify-between">
            <button
              type="button"
              onClick={handleButtonClick}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={uploading}
            >
              Select File
            </button>
            <button
              type="submit"
              className={`px-4 py-2 text-sm font-medium text-white rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                ${file && !uploading
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-400 cursor-not-allowed'}`}
              disabled={!file || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FileDrop; 