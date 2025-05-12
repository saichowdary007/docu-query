import axios from 'axios';

// Get API URL from environment variable or use default
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Upload file to the server
 * @param {File} file - File to upload
 * @returns {Promise} - Promise with upload result
 */
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    // Let the browser set the Content-Type header automatically for FormData
    const response = await axios.post(`${API_URL}/upload`, formData);
    return response.data;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
};

/**
 * Send chat message to the server
 * @param {string} query - User query
 * @param {Array} history - Chat history
 * @returns {Promise} - Promise with chat response
 */
export const sendChatMessage = async (query, history = []) => {
  const formData = new FormData();
  formData.append('query', query);
  
  if (history && history.length > 0) {
    formData.append('history', JSON.stringify(history));
  }
  
  try {
    // Let the browser set the Content-Type header automatically for FormData
    const response = await axios.post(`${API_URL}/chat`, formData);
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Export data using SQL query
 * @param {string} sql - SQL query to execute
 * @returns {string} - URL to download the exported file
 */
export const exportData = (sql) => {
  return `${API_URL}/export?sql=${encodeURIComponent(sql)}`;
};

export default {
  uploadFile,
  sendChatMessage,
  exportData,
}; 