import { useState } from 'react';
import FileDrop from './components/FileDrop';
import ChatWindow from './components/ChatWindow';
import DocumentManager from './components/DocumentManager';
import './index.css';

function App() {
  const [activeFile, setActiveFile] = useState(null); 
  const [uploaded, setUploaded] = useState(false);
  const [view, setView] = useState('upload'); // 'upload', 'chat', or 'documents'

  const handleUploadSuccess = (fileData) => {
    setUploaded(true);
    setActiveFile(fileData);
    // Switch to chat view after successful upload
    setView('chat');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <span className="text-blue-600 mr-2">📑</span>
            DocuQuery AI
          </h1>
          <nav className="flex space-x-4">
            <button 
              onClick={() => setView('upload')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                view === 'upload' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Upload
            </button>
            <button 
              onClick={() => setView('documents')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                view === 'documents' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Documents
            </button>
            <button 
              onClick={() => setView('chat')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                view === 'chat' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
              disabled={!uploaded}
            >
              Chat
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {view === 'upload' && (
            <div className="rounded-lg h-96">
              <FileDrop onUploadSuccess={handleUploadSuccess} />
            </div>
          )}

          {view === 'documents' && (
            <div className="rounded-lg">
              <DocumentManager onUploadSuccess={handleUploadSuccess} />
            </div>
          )}

          {view === 'chat' && uploaded && (
            <div className="rounded-lg h-[calc(100vh-12rem)] border border-gray-300 bg-white">
              <div className="flex h-full flex-col">
                <div className="bg-gray-100 py-2 px-4 border-b flex justify-between items-center">
                  <div className="flex items-center">
                    <span className="text-lg mr-2">
                      {activeFile?.name?.endsWith('.pdf') ? '📕' : 
                       activeFile?.name?.endsWith('.docx') ? '📘' : 
                       activeFile?.name?.endsWith('.xlsx') || activeFile?.name?.endsWith('.csv') ? '📊' : '📄'}
                    </span>
                    <h2 className="text-sm font-medium text-gray-700 truncate max-w-sm">
                      {activeFile?.name || 'Chat'}
                    </h2>
                  </div>
                  <div className="text-xs text-gray-500">
                    Ask questions about your document
                  </div>
                </div>
                <div className="flex-1 overflow-hidden">
                  <ChatWindow />
                </div>
              </div>
            </div>
          )}
          
          {view === 'chat' && !uploaded && (
            <div className="rounded-lg h-96 border border-gray-300 bg-white flex items-center justify-center">
              <div className="text-center p-6">
                <svg 
                  className="mx-auto h-12 w-12 text-gray-400" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24" 
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth="2" 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                  />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No document uploaded</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Please upload a document first to start chatting.
                </p>
                <button
                  onClick={() => setView('upload')}
                  className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  Go to Upload
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            DocuQuery AI - Intelligent document analysis powered by RAG technology
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App; 