'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiUrls } from './api'
import Cookies from 'js-cookie'

// Define user type
export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  role: string
  created_at: string
  profile_picture?: string | null
}

// Define auth state
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

// Define auth context
interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  loginWithGoogle: (token: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

// Create auth context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Auth provider props
interface AuthProviderProps {
  children: ReactNode
}

// Cookie names
const TOKEN_COOKIE = 'docuquery_token'
const REFRESH_TOKEN_COOKIE = 'docuquery_refresh_token'

// Cookie options for better security
const COOKIE_OPTIONS = {
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'strict' as const,
  expires: 7, // 7 days
  path: '/'
}

export function AuthProvider({ children }: AuthProviderProps) {
  // Auth state
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  })

  // Load user from storage on mount
  useEffect(() => {
    const loadUser = async () => {
      const token = Cookies.get(TOKEN_COOKIE)
      
      if (!token) {
        setState(prev => ({ ...prev, isLoading: false }))
        return
      }
      
      try {
        const response = await fetch(apiUrls.userProfile, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        })
        
        if (response.ok) {
          const user = await response.json()
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } else {
          // Try to refresh token
          await refreshToken()
        }
      } catch (error) {
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: 'Failed to load user profile'
        })
        
        // Clear invalid tokens
        Cookies.remove(TOKEN_COOKIE)
        Cookies.remove(REFRESH_TOKEN_COOKIE)
      }
    }
    
    loadUser()
  }, [])
  
  // Refresh token function
  const refreshToken = async () => {
    const refreshToken = Cookies.get(REFRESH_TOKEN_COOKIE)
    
    if (!refreshToken) {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      })
      return false // Return false to indicate refresh failed
    }
    
    try {
      const response = await fetch(apiUrls.refreshToken, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
        credentials: 'include'
      })
      
      if (response.ok) {
        const { access_token } = await response.json()
        Cookies.set(TOKEN_COOKIE, access_token, COOKIE_OPTIONS)
        
        // Fetch user profile with new token
        const userResponse = await fetch(apiUrls.userProfile, {
          headers: {
            'Authorization': `Bearer ${access_token}`
          },
          credentials: 'include'
        })
        
        if (userResponse.ok) {
          const user = await userResponse.json()
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
          return true // Return true to indicate refresh succeeded
        } else {
          throw new Error('Failed to load user profile')
        }
      } else {
        throw new Error('Failed to refresh token')
      }
    } catch (error) {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Session expired. Please login again.'
      })
      
      // Clear invalid tokens
      Cookies.remove(TOKEN_COOKIE)
      Cookies.remove(REFRESH_TOKEN_COOKIE)
      return false // Return false to indicate refresh failed
    }
  }
  
  // Login function
  const login = async (email: string, password: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))
    console.log(`Logging in user: ${email}`)
    
    try {
      // Use URLSearchParams to format the request body as form data
      const formData = new URLSearchParams()
      formData.append('username', email)  // OAuth2 spec uses 'username' field
      formData.append('password', password)
      
      const response = await fetch(apiUrls.login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData.toString(),
        credentials: 'include'
      })
      
      if (response.ok) {
        const { access_token, refresh_token } = await response.json()
        console.log('Login successful, received tokens')
        
        // Save tokens as cookies
        try {
          Cookies.set(TOKEN_COOKIE, access_token, COOKIE_OPTIONS)
          Cookies.set(REFRESH_TOKEN_COOKIE, refresh_token, COOKIE_OPTIONS)
          
          // Verify cookies were set
          const savedToken = Cookies.get(TOKEN_COOKIE)
          const savedRefreshToken = Cookies.get(REFRESH_TOKEN_COOKIE)
          
          if (!savedToken || !savedRefreshToken) {
            console.error('Failed to save tokens as cookies')
            if (!savedToken) console.error('Access token not saved')
            if (!savedRefreshToken) console.error('Refresh token not saved')
          } else {
            console.log('Tokens successfully saved as cookies')
          }
        } catch (cookieError) {
          console.error('Error saving cookies:', cookieError)
        }
        
        // Fetch user profile
        console.log('Fetching user profile with token')
        const userResponse = await fetch(apiUrls.userProfile, {
          headers: {
            'Authorization': `Bearer ${access_token}`
          },
          credentials: 'include'
        })
        
        if (userResponse.ok) {
          const user = await userResponse.json()
          console.log('User profile retrieved:', user.email)
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } else {
          const errorData = await userResponse.json()
          console.error('Failed to load user profile:', errorData)
          throw new Error('Failed to load user profile')
        }
      } else {
        const errorData = await response.json()
        console.error('Login failed:', errorData)
        throw new Error(errorData.detail || 'Login failed')
      }
    } catch (error) {
      console.error('Login error:', error)
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Login failed'
      }))
    }
  }
  
  // Register function
  const register = async (email: string, password: string, fullName?: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))
    console.log(`Registering user: ${email}`)
    
    try {
      const response = await fetch(apiUrls.register, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null
        }),
        credentials: 'include'
      })
      
      if (response.ok) {
        console.log('Registration successful, auto-logging in')
        // Auto login after successful registration
        await login(email, password)
      } else {
        const errorData = await response.json()
        console.error('Registration failed:', errorData)
        throw new Error(errorData.detail || 'Registration failed')
      }
    } catch (error) {
      console.error('Registration error:', error)
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Registration failed'
      }))
    }
  }
  
  // Google login function
  const loginWithGoogle = async (token: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))
    console.log('Starting Google login process')
    
    try {
      const response = await fetch(apiUrls.googleAuth, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token }),
        credentials: 'include'
      })
      
      if (response.ok) {
        const { access_token, refresh_token } = await response.json()
        console.log('Google login successful, received tokens')
        
        // Save tokens as cookies
        try {
          Cookies.set(TOKEN_COOKIE, access_token, COOKIE_OPTIONS)
          Cookies.set(REFRESH_TOKEN_COOKIE, refresh_token, COOKIE_OPTIONS)
          
          // Verify cookies were set
          const savedToken = Cookies.get(TOKEN_COOKIE)
          const savedRefreshToken = Cookies.get(REFRESH_TOKEN_COOKIE)
          
          if (!savedToken || !savedRefreshToken) {
            console.error('Failed to save tokens as cookies')
            if (!savedToken) console.error('Access token not saved')
            if (!savedRefreshToken) console.error('Refresh token not saved')
          } else {
            console.log('Tokens successfully saved as cookies')
          }
        } catch (cookieError) {
          console.error('Error saving cookies:', cookieError)
        }
        
        // Fetch user profile
        console.log('Fetching user profile with token')
        const userResponse = await fetch(apiUrls.userProfile, {
          headers: {
            'Authorization': `Bearer ${access_token}`
          },
          credentials: 'include'
        })
        
        if (userResponse.ok) {
          const user = await userResponse.json()
          console.log('User profile retrieved from Google login:', user.email)
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } else {
          const errorData = await userResponse.json()
          console.error('Failed to load Google user profile:', errorData)
          throw new Error('Failed to load user profile')
        }
      } else {
        const errorData = await response.json()
        console.error('Google login failed:', errorData)
        throw new Error(errorData.detail || 'Google login failed')
      }
    } catch (error) {
      console.error('Google login error:', error)
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Google login failed'
      }))
    }
  }
  
  // Logout function
  const logout = () => {
    Cookies.remove(TOKEN_COOKIE)
    Cookies.remove(REFRESH_TOKEN_COOKIE)
    
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null
    })
  }
  
  // Clear error function
  const clearError = () => {
    setState(prev => ({ ...prev, error: null }))
  }
  
  // Create context value
  const contextValue: AuthContextType = {
    ...state,
    login,
    register,
    loginWithGoogle,
    logout,
    clearError
  }
  
  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

// Auth context hook
export function useAuth() {
  const context = useContext(AuthContext)
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  
  return context
} 