/**
 * API configuration for the application
 */

// Get the base URL from environment variables or default to localhost
export const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
};

// Construct API URLs
export const apiUrls = {
  chat: `${getApiBaseUrl()}/api/v1/chat/query`,
  fileUpload: `${getApiBaseUrl()}/api/v1/files/upload`,
  filesList: `${getApiBaseUrl()}/api/v1/files/uploaded-files`,
  fileDelete: (filename: string) => `${getApiBaseUrl()}/api/v1/files/delete/${filename}`,
  fileDownload: `${getApiBaseUrl()}/api/v1/files/download-filtered`,
};

// Get API key from environment variables
export const getApiKey = () => {
  return process.env.NEXT_PUBLIC_BACKEND_API_KEY || 'secret_api_key_123';
}; 