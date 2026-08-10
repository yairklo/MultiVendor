import fs from 'fs';
import path from 'path';

// The suite's individual specs used to each log in via the UI in their own
// beforeEach. With enough spec files that adds up fast and trips the
// backend's 10/minute rate limit on /api/v1/auth/login (real 429s, not
// flakiness) partway through a full run. Logging in once here and sharing
// the resulting session via storageState avoids that entirely, and is
// faster besides. Specs that specifically test the login/unauthenticated
// flow (auth.spec.ts, session-expiration.spec.ts) opt out with
// `test.use({ storageState: { cookies: [], origins: [] } })`.
async function globalSetup() {
  const backendURL = 'http://localhost:8000';

  const response = await fetch(`${backendURL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'admin@test-tenant.com',
      password: 'admin123',
      tenant_slug: 'test-tenant',
    }),
  });

  if (!response.ok) {
    throw new Error(`e2e global-setup: login failed with ${response.status}. Is the backend seeded (server/seed_db.py)?`);
  }

  const data = await response.json();

  const storageState = {
    cookies: [
      { name: 'token', value: data.access_token, domain: 'localhost', path: '/', expires: -1, httpOnly: false, secure: false, sameSite: 'Lax' as const },
      { name: 'tenantSlug', value: 'test-tenant', domain: 'localhost', path: '/', expires: -1, httpOnly: false, secure: false, sameSite: 'Lax' as const },
    ],
    origins: [],
  };

  const authDir = path.join(__dirname, '.auth');
  fs.mkdirSync(authDir, { recursive: true });
  fs.writeFileSync(path.join(authDir, 'admin.json'), JSON.stringify(storageState, null, 2));
}

export default globalSetup;
