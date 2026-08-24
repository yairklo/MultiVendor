import '@testing-library/jest-dom'
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './src/mocks/server'

// proxy.ts reads this at module load time to verify JWT signatures -- must
// be set before any test file imports it.
process.env.JWT_SECRET_KEY = 'test-jwt-secret-for-vitest'

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

