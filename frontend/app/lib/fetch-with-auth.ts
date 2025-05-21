import Cookies from 'js-cookie';
import { apiUrls } from './api';

const TOKEN_COOKIE = 'docuquery_token';
const REFRESH_TOKEN_COOKIE = 'docuquery_refresh_token';

/**
 * Wrapper around fetch that handles authentication
 * - Adds Authorization header with token
 * - Refreshes token if needed
 * - Redirects to login page if auth fails
 */
export async function fetchWithAuth(
  url: string, 
  options: RequestInit = {}, 
  retrying: boolean = false
): Promise<Response> {
  const token = Cookies.get(TOKEN_COOKIE);
  
  // Add Authorization header if token exists
  const headers = {
    ...options.headers,
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
  
  // Make the request
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include'
  });
  
  // Handle 401 Unauthorized errors
  if (response.status === 401 && !retrying) {
    // Try to refresh the token
    const refreshed = await refreshToken();
    
    if (refreshed) {
      // Retry the request with the new token
      return fetchWithAuth(url, options, true);
    } else {
      // Redirect to login page if refresh failed
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  }
  
  return response;
}

/**
 * Refreshes the access token using the refresh token
 * @returns true if token was refreshed successfully, false otherwise
 */
async function refreshToken(): Promise<boolean> {
  const refreshToken = Cookies.get(REFRESH_TOKEN_COOKIE);
  
  if (!refreshToken) {
    return false;
  }
  
  try {
    const response = await fetch(apiUrls.refreshToken, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: 'include'
    });
    
    if (response.ok) {
      const { access_token, refresh_token } = await response.json();
      
      // Save the new tokens
      Cookies.set(TOKEN_COOKIE, access_token, {
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        expires: 7,
        path: '/'
      });
      
      if (refresh_token) {
        Cookies.set(REFRESH_TOKEN_COOKIE, refresh_token, {
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'strict',
          expires: 30,
          path: '/'
        });
      }
      
      return true;
    }
  } catch (error) {
    console.error('Error refreshing token:', error);
  }
  
  // Clear invalid tokens
  Cookies.remove(TOKEN_COOKIE);
  Cookies.remove(REFRESH_TOKEN_COOKIE);
  return false;
} 