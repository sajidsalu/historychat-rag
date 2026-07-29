import { useState } from 'react'

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export default function PersonalityCard({ personality, onClick }) {
  const [imgFailed, setImgFailed] = useState(false)
  const showPhoto = Boolean(personality.photo_url) && !imgFailed

  return (
    <button type="button" className="person-card" onClick={onClick}>
      <div className="avatar">
        {showPhoto ? (
          <img
            src={personality.photo_url}
            alt={personality.name}
            onError={() => setImgFailed(true)}
          />
        ) : (
          <span>{initials(personality.name)}</span>
        )}
      </div>
      <div className="person-meta">
        <strong>{personality.name}</strong>
        <span className={`status-pill status-${personality.status}`}>
          {personality.status}
        </span>
      </div>
    </button>
  )
}
