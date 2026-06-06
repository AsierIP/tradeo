import { NextRequest, NextResponse } from 'next/server'

const apiBase = process.env.TRADEO_API_INTERNAL_URL || 'http://backend:8000/api'
const username = process.env.TRADEO_ADMIN_USERNAME || 'admin'
const password = process.env.TRADEO_ADMIN_PASSWORD || 'change-me'

function authHeader() {
  return `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`
}

async function forward(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join('/')
  const url = `${apiBase}/${path}${req.nextUrl.search}`
  const body = req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.text()
  let res: Response
  try {
    res = await fetch(url, {
      method: req.method,
      headers: {
        Authorization: authHeader(),
        'Content-Type': req.headers.get('content-type') || 'application/json'
      },
      body,
      cache: 'no-store'
    })
  } catch (err) {
    return NextResponse.json(
      { detail: 'Backend not ready', error: err instanceof Error ? err.message : 'fetch failed' },
      { status: 503 }
    )
  }
  const text = await res.text()
  return new NextResponse(text, {
    status: res.status,
    headers: {
      'Content-Type': res.headers.get('content-type') || 'application/json'
    }
  })
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}
