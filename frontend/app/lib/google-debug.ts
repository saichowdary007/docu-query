/**
 * This utility file provides debugging functions for Google Sign-In
 */

/**
 * Returns the current origin that needs to be added to Google Cloud Console
 */
export function getOriginForGoogleConsole() {
  if (typeof window === 'undefined') {
    console.log('Cannot determine origin: window is not defined (server-side context)');
    return null;
  }
  
  const origin = window.location.origin;
  console.log(`Current origin: ${origin}`);
  console.log(`Add this URL to Google Cloud Console > API & Services > Credentials > OAuth 2.0 Client ID > Authorized JavaScript origins`);
  return origin;
}

/**
 * Use this function to check your Google OAuth configuration
 */
export function checkGoogleConfig() {
  if (typeof window === 'undefined') {
    return null;
  }

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const origin = window.location.origin;
  
  console.log('------- Google Sign-In Debugging -------');
  console.log(`Google Client ID present: ${!!clientId}`);
  console.log(`Current origin: ${origin}`);
  
  if (!clientId) {
    console.error('Missing Google Client ID. Create .env.local with NEXT_PUBLIC_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID');
  } else {
    console.log(`Client ID: ${clientId.substring(0, 8)}...${clientId.substring(clientId.length - 8)}`);
    console.log('Make sure this origin is authorized in Google Cloud Console');
  }
  
  console.log('--------------------------------------');
} 