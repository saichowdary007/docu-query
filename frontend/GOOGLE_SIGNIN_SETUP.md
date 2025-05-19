# Google Sign-In Setup for DocuQuery-AI

## Issues
1. **Domain Not Authorized**: Error "[GSI_LOGGER]: The given origin is not allowed for the given client ID."
2. **Missing Client ID**: Google Client ID environment variable may not be set.

## Solutions

### 1. Create a Google OAuth Client ID
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Configure the OAuth consent screen
6. For Application type, select "Web application"
7. Add authorized JavaScript origins:
   - `http://localhost:3000` (for local development)
   - `http://127.0.0.1:3000` (alternative local development URL)
   - Your production domain (if applicable)
8. Click "Create"
9. Note down your Client ID

### 2. Set up environment variables
Create a `.env.local` file in the `frontend` directory with the following content:

```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
```

Replace `YOUR_GOOGLE_CLIENT_ID` with the actual Client ID you created.

### 3. Fix "Origin Not Allowed" Error
If you're seeing the error "[GSI_LOGGER]: The given origin is not allowed for the given client ID":

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Find and click on your OAuth 2.0 Client ID
4. Under "Authorized JavaScript origins," add the URL you're using to access your app:
   - Make sure you include the protocol (`http://` or `https://`)
   - Don't include paths, just the domain and port if applicable
   - Examples:
     - `http://localhost:3000`
     - `https://your-production-domain.com`
5. Click "Save"
6. Note: Changes may take a few minutes to propagate

### 4. Testing
1. Restart your Next.js development server
2. The Google Sign-In button should now appear and function correctly on both login and register pages
3. Check the browser console for any errors

### 5. Troubleshooting
- **Button doesn't render**: Check if you've allowed proper time for the Google API script to load
- **"Not authorized" errors persist**: Make sure you've added EXACTLY the same origin URL that appears in your browser address bar
- **"Invalid client ID" errors**: Verify your Client ID is correctly copied to your .env.local file

### Note
- In production environments like Vercel, add `NEXT_PUBLIC_GOOGLE_CLIENT_ID` as an environment variable in the project settings.
- The backend also needs to be correctly configured to handle Google authentication tokens. 