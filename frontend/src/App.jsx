import React, { useState } from 'react';
import FileDrop from './components/FileDrop';
import ChatWindow from './components/ChatWindow';
import './index.css';

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  
  const handleFileUploaded = (fileInfo) => {
    setUploadedFiles(prev => [...prev, fileInfo]);
  };
  
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">
              DocuQuery
            </h1>
            <div className="text-sm text-gray-500">
              RAG-powered document assistant
            </div>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex flex-col md:flex-row gap-6 h-[calc(100vh-200px)]">
            {/* Left sidebar */}
            <div className="w-full md:w-1/3 flex flex-col space-y-6">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Upload Documents</h2>
                <FileDrop onFileUploaded={handleFileUploaded} />
              </div>
              
              {uploadedFiles.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6 flex-grow overflow-auto">
                  <h2 className="text-lg font-medium text-gray-900 mb-4">Uploaded Files</h2>
                  <ul className="divide-y divide-gray-200">
                    {uploadedFiles.map((file, index) => (
                      <li key={index} className="py-3">
                        <div className="flex items-center space-x-4">
                          <div className="flex-shrink-0">
                            {file.file_type === 'pdf' && (
                              <svg className="h-6 w-6 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                              </svg>
                            )}
                            {file.file_type === 'docx' && (
                              <svg className="h-6 w-6 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                              </svg>
                            )}
                            {file.file_type === 'pptx' && (
                              <svg className="h-6 w-6 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                              </svg>
                            )}
                            {file.file_type === 'tabular' && (
                              <svg className="h-6 w-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M5 4a1 1 0 011-1h8a1 1 0 011 1v1H5V4zm4 3V6h6v1H9zm6 2v1H9V9h6zm0 2v1H9v-1h6zm-6 3v-1h6v1H9zm-4-5H4v1h1v-1zm0-2H4v1h1V7zm0 4H4v1h1v-1zm0 2H4v1h1v-1z" clipRule="evenodd" />
                              </svg>
                            )}
                            {file.file_type === 'text' && (
                              <svg className="h-6 w-6 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                              </svg>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {file.file_name}
                            </p>
                            <p className="text-sm text-gray-500">
                              {file.chunks_count} chunks indexed
                            </p>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            {/* Chat area */}
            <div className="w-full md:w-2/3 flex flex-col">
              <ChatWindow />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App; 