'use client'

import { useEffect, useRef, useState } from 'react'
import { getGoogleClientId } from '../lib/api'

interface GoogleSignInButtonProps {
  onSuccess: (credential: string) => Promise<void>
  text?: 'signin_with' | 'signup_with' | 'continue_with'
  theme?: 'outline' | 'filled_blue' | 'filled_black'
}

export default function GoogleSignInButton({ 
  onSuccess, 
  text = 'signin_with',
  theme = 'outline' 
}: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [isRendered, setIsRendered] = useState(false)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    // Skip server-side rendering
    if (typeof window === 'undefined') return

    const googleClientId = getGoogleClientId()
    
    if (!googleClientId) {
      console.error("Google Client ID missing")
      setHasError(true)
      return
    }

    // Make sure the ref exists
    if (!buttonRef.current) {
      return
    }

    // Clean any previous content
    buttonRef.current.innerHTML = ''
    
    const handleCredentialResponse = (response: any) => {
      if (response?.credential) {
        console.log("Google sign-in successful, processing credential")
        onSuccess(response.credential)
      }
    }
    
    const loadAndInitialize = () => {
      if (!window.google) {
        console.error("Google API not available")
        setHasError(true)
        return
      }

      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true
        })
        
        window.google.accounts.id.renderButton(buttonRef.current!, {
          type: 'standard',
          theme: theme,
          size: 'large',
          text: text,
          shape: 'rectangular',
          width: 280
        })
        
        setIsRendered(true)
        setHasError(false)
      } catch (error) {
        console.error("Error initializing Google Sign-In:", error)
        setHasError(true)
      }
    }
    
    // Check if Google API is already loaded
    if (window.google?.accounts) {
      loadAndInitialize()
      return
    }
    
    // Load the Google API script
    if (!document.querySelector('script#google-gsi-script')) {
      const script = document.createElement('script')
      script.id = 'google-gsi-script'
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.onload = loadAndInitialize
      script.onerror = () => setHasError(true)
      document.body.appendChild(script)
    }
    
    // If script exists but hasn't initialized correctly
    const checkInterval = setInterval(() => {
      if (window.google?.accounts) {
        clearInterval(checkInterval)
        loadAndInitialize()
      }
    }, 100)
    
    // Cleanup function
    return () => {
      clearInterval(checkInterval)
    }
  }, [onSuccess, text, theme])
  
  if (hasError) {
    return (
      <div className="text-center">
        <p className="text-sm text-amber-600 dark:text-amber-400">
          Google Sign-In unavailable. {window?.location?.origin && (
            <>
              Add <strong>{window.location.origin}</strong> to authorized origins.
            </>
          )}
        </p>
      </div>
    )
  }
  
  return (
    <div 
      ref={buttonRef} 
      className="h-10 flex items-center justify-center"
      aria-label="Google Sign-In Button"
    />
  )
} 