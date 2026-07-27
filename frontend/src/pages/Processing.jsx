import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { personalitiesApi } from '../api'
import { useAuth } from '../AuthContext'

export default function Processing() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { token } = useAuth()
  const [status, setStatus] = useState(location.state?.failed ? 'failed' : 'processing')
  const [name, setName] = useState(location.state?.name || 'This figure')
  const [error, setError] = useState('')
  const nameRef = useRef(name)
  nameRef.current = name

  useEffect(() => {
    let cancelled = false
    let timer

    async function poll() {
      try {
        const data = await personalitiesApi.status(token, id)
        if (cancelled) return
        setStatus(data.status)
        if (data.status === 'ready') {
          navigate(`/chat/${id}`, {
            replace: true,
            state: { name: nameRef.current },
          })
          return
        }
        if (data.status === 'failed') {
          setError(
            `Couldn’t prepare ${nameRef.current}. The Wikipedia lookup may have failed — try a different name from Home.`
          )
          return
        }
        timer = setTimeout(poll, 2000)
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setStatus('failed')
        }
      }
    }

    ;(async () => {
      try {
        const list = await personalitiesApi.list(token)
        const match = list.find((p) => String(p.id) === String(id))
        if (match && !cancelled) {
          setName(match.name)
          nameRef.current = match.name
          setStatus(match.status)
          if (match.status === 'ready') {
            navigate(`/chat/${id}`, {
              replace: true,
              state: { name: match.name },
            })
            return
          }
          if (match.status === 'failed') {
            setError(
              `Couldn’t prepare ${match.name}. The Wikipedia lookup may have failed — try a different name from Home.`
            )
            return
          }
        }
      } catch {
        // polling still works without the list
      }
      if (!cancelled) poll()
    })()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [id, token, navigate])

  return (
    <div className="page page-center">
      <div className="panel">
        <Link to="/home" className="back-link">
          ← Back to Home
        </Link>
        <h1>Preparing {name}</h1>
        {status !== 'failed' ? (
          <>
            <div className="spinner" aria-hidden="true" />
            <p className="muted">
              Fetching source material and building embeddings…
              <br />
              Status: <strong>{status}</strong>
            </p>
          </>
        ) : (
          <>
            <p className="error">{error || 'Something went wrong.'}</p>
            <Link className="btn primary" to="/home">
              Back to Home
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
