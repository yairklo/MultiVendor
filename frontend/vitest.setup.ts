import '@testing-library/jest-dom'
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './src/mocks/server'

// proxy.ts reads these at module load time -- must be set before any test
// file imports it.
process.env.JWT_SECRET_KEY = 'test-jwt-secret-for-vitest' // verifies JWT signatures
process.env.APP_DOMAIN = 'app.example.com' // the platform's own domain, for custom-domain rewrite tests
process.env.INTERNAL_API_BASE_URL = 'http://localhost:8000' // same origin the MSW handlers below mock

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

