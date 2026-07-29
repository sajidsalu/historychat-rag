import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { chatApi, personalitiesApi } from '../api'
import { useAuth } from '../AuthContext'

export default function Chat() {
  const { id } = useParams()
  const location = useLocation()
  const { token } = useAuth()
  const [name, setName] = useState(location.state?.name || '…')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [inFlight, setInFlight] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [history, people] = await Promise.all([
          personalitiesApi.messages(token, id),
          personalitiesApi.list(token),
        ])
        if (cancelled) return
        const match = people.find((p) => String(p.id) === String(id))
        if (match) setName(match.name)
        setMessages(
          history.map((m) => ({
            role: m.role === 'assistant' ? 'bot' : 'user',
            content: m.content,
            has_sources: false,
            sources: [],
          }))
        )
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoadingHistory(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, token])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages, inFlight])

  async function onSubmit(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || inFlight) return

    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInFlight(true)

    try {
      const data = await chatApi.send(token, Number(id), text)
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          content: data.reply || 'No reply returned.',
          has_sources: Boolean(data.has_sources),
          sources: Array.isArray(data.sources) ? data.sources : [],
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: `Error: ${err.message}`, has_sources: false, sources: [] },
      ])
    } finally {
      setInFlight(false)
    }
  }

  return (
    <div className="chat-shell">
      <header className="header">
        <div className="brand">
          <h1>{name}</h1>
          <p className="disclaimer">AI simulation — not the real person’s views</p>
        </div>
        <Link to="/home" className="back-link header-back">
          Back to Home
        </Link>
      </header>

      <main className="messages" ref={listRef} aria-live="polite">
        {loadingHistory ? (
          <div className="empty">Loading conversation…</div>
        ) : messages.length === 0 && !inFlight ? (
          <div className="empty">Ask {name} a question to start the conversation.</div>
        ) : (
          messages.map((m, i) =>
            m.role === 'user' ? (
              <div className="msg user" key={`u-${i}`}>
                <div className="bubble">{m.content}</div>
              </div>
            ) : (
              <div className="msg bot" key={`b-${i}`}>
                <div className="msg-label">{name}</div>
                <div className="bubble">{m.content}</div>
                {m.has_sources ? (
                  <details className="sources-panel">
                    <summary>Sources used ({m.sources.length})</summary>
                    <div className="sources-list">
                      {m.sources.map((source, idx) => (
                        <div className="source-item" key={`s-${i}-${idx}`}>
                          <span className="source-snippet">{source.text}</span>
                          <span className="source-score">
                            {Math.round((source.score || 0) * 100)}% match
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                ) : null}
              </div>
            )
          )
        )}

        {inFlight ? (
          <div className="msg bot">
            <div className="msg-label">{name}</div>
            <div className="bubble">
              <div className="typing" aria-label="Typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        ) : null}
      </main>

      {error ? <p className="error chat-error">{error}</p> : null}

      <form className="composer" onSubmit={onSubmit}>
        <input
          type="text"
          placeholder="Ask something…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={inFlight || loadingHistory}
          aria-label="Message"
          required
        />
        <button type="submit" disabled={inFlight || loadingHistory}>
          Send
        </button>
      </form>
    </div>
  )
}
