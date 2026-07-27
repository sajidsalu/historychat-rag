import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { personalitiesApi } from '../api'
import { useAuth } from '../AuthContext'

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

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
      routeForPersonality(personality, navigate)
    } catch (err) {
      setError(err.message)
    } finally {
      setSearching(false)
    }
  }

  function onCardClick(personality) {
    if (personality.status === 'ready') {
      navigate(`/chat/${personality.id}`, { state: { name: personality.name } })
      return
    }
    // pending/processing/failed → processing screen (can retry failed via search)
    navigate(`/processing/${personality.id}`, { state: { name: personality.name } })
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>HistoryChat</h1>
          <p className="muted small">Signed in as {email}</p>
        </div>
        <button type="button" className="btn ghost" onClick={() => { logout(); navigate('/login') }}>
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

        {error ? <p className="error">{error}</p> : null}
        {loading ? <p className="muted">Loading personalities…</p> : null}

        <div className="card-grid">
          {people.map((p) => (
            <button
              key={p.id}
              type="button"
              className="person-card"
              onClick={() => onCardClick(p)}
            >
              <div className="avatar">
                {p.photo_url ? (
                  <img src={p.photo_url} alt="" />
                ) : (
                  <span>{initials(p.name)}</span>
                )}
              </div>
              <div className="person-meta">
                <strong>{p.name}</strong>
                <span className={`status-pill status-${p.status}`}>{p.status}</span>
              </div>
            </button>
          ))}
        </div>
      </main>
    </div>
  )
}
