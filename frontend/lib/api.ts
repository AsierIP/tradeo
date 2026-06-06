export const API_URL = '/api/tradeo'

export async function fetcher(path: string) {
  const clean = path.replace(/^\//, '')
  const res = await fetch(`${API_URL}/${clean}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export async function postJson(path: string, body: unknown = {}) {
  const clean = path.replace(/^\//, '')
  const res = await fetch(`${API_URL}/${clean}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}
