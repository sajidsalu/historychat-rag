import { createContext, useContext, useMemo, useState } from 'react'
import { authApi } from './api'

const TOKEN_KEY = 'historychat_token'
const EMAIL_KEY = 'historychat_email'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [email, setEmail] = useState(() => localStorage.getItem(EMAIL_KEY))

  const value = useMemo(() => {
    function persist(nextToken, nextEmail) {
      setToken(nextToken)
      setEmail(nextEmail)
      if (nextToken) {
        localStorage.setItem(TOKEN_KEY, nextToken)
        localStorage.setItem(EMAIL_KEY, nextEmail || '')
      } else {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(EMAIL_KEY)
      }
    }

    async function signup(emailValue, password) {
      const data = await authApi.signup(emailValue, password)
      persist(data.access_token, data.email)
      return data
    }

    async function login(emailValue, password) {
      const data = await authApi.login(emailValue, password)
      persist(data.access_token, data.email)
      return data
    }

    function logout() {
      persist(null, null)
    }

    return {
      token,
      email,
      isAuthenticated: Boolean(token),
      signup,
      login,
      logout,
    }
  }, [token, email])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
