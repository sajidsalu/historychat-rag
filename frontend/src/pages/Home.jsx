import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { personalitiesApi } from '../api'
import { useAuth } from '../AuthContext'
import PersonalityCard from '../components/PersonalityCard'

function routeForPersonality(personality, navigate) {
  if (personality.status === 'ready') {
    navigate(`/chat/${personality.id}`, { state: { name: personality.name } })
  } else if (personality.status === 'failed') {
    navigate(`/processing/${personality.id}`, {
      state: { name: personality.name, failed: true },
    })
  } else {
    navigate(`/processing/${personality.id}`, { state: { name: personality.name } })
  }
}

export default function Home() {
  const { token, email, logout } = useAuth()
  const navigate = useNavigate()
  const [people, setPeople] = useState([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await personalitiesApi.list(token)
        if (!cancelled) setPeople(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  async function onSearch(e) {
    e.preventDefault()
    const name = query.trim()
    if (!name) return
    setError('')
    setSearching(true)
    try {
      const personality = await personalitiesApi.search(token, name)
      // Refresh list so new cards (with photos) appear when user comes back
      try {
        setPeople(await personalitiesApi.list(token))
      } catch {
        // ignore refresh errors
      }
      routeForPersonality(personality, navigate)
    } catch (err) {
      if (err.status === 404) {
        setError('No historical figure found — try a different name')
      } else {
        setError(err.message || 'Search failed')
      }
    } finally {
      setSearching(false)
    }
  }

  function onCardClick(personality) {
    if (personality.status === 'ready') {
      navigate(`/chat/${personality.id}`, { state: { name: personality.name } })
      return
    }
    navigate(`/processing/${personality.id}`, { state: { name: personality.name } })
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>HistoryChat</h1>
          <p className="muted small">Signed in as {email}</p>
        </div>
        <button
          type="button"
          className="btn ghost"
          onClick={() => {
            logout()
            navigate('/login')
          }}
        >
          Log out
        </button>
      </header>

      <main className="content">
        <form className="search-bar" onSubmit={onSearch}>
          <input
            type="text"
            placeholder="Search a historical figure (e.g. Gandhi)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search personality"
          />
          <button className="btn primary" type="submit" disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>

        {error ? <p className="error search-error">{error}</p> : null}
        {loading ? <p className="muted">Loading personalities…</p> : null}

        <div className="card-grid">
          {people.map((p) => (
            <PersonalityCard
              key={p.id}
              personality={p}
              onClick={() => onCardClick(p)}
            />
          ))}
        </div>
      </main>
    </div>
  )
}
