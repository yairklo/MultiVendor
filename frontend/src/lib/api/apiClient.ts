export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export const apiClient = async (url: string, options: RequestInit = {}) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  // Handle relative URLs in Node/Test environment
  const fullUrl = url.startsWith('/') ? `http://localhost:3000${url}` : url

  const response = await fetch(fullUrl, { ...options, headers })

  if (!response.ok) {
    throw new ApiError(response.status, `HTTP Error ${response.status}`)
  }
  
  if (response.status === 204) return null
  return response.json()
}
