/**
 * API configuration for the application
 */

// Get the base URL from environment variables or default to localhost
export const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
};

// Construct API URLs
export const apiUrls = {
  // Chat and file endpoints
  chat: `${getApiBaseUrl()}/api/v1/queries/query`,
  fileUpload: `${getApiBaseUrl()}/api/v1/files/upload`,
  filesList: `${getApiBaseUrl()}/api/v1/files/uploaded-files`,
  fileDelete: (filename: string) => `${getApiBaseUrl()}/api/v1/files/delete/${filename}`,
  fileDownload: `${getApiBaseUrl()}/api/v1/files/download-filtered`,
  
  // Authentication endpoints
  register: `${getApiBaseUrl()}/api/v1/auth/register`,
  login: `${getApiBaseUrl()}/api/v1/auth/login`,
  googleAuth: `${getApiBaseUrl()}/api/v1/auth/google`,
  refreshToken: `${getApiBaseUrl()}/api/v1/auth/refresh`,
  userProfile: `${getApiBaseUrl()}/api/v1/auth/me`,
};

// Get API key from environment variables
export const getApiKey = () => {
  return process.env.NEXT_PUBLIC_BACKEND_API_KEY || 'secret_api_key_123';
};

// Google OAuth client ID
export const getGoogleClientId = () => {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
  
  if (!clientId) {
    console.warn('NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set in environment variables.');
    console.log('Create a .env.local file in the frontend directory with NEXT_PUBLIC_GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID');
  }
  
  return clientId;
}; 