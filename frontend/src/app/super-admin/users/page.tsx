import { adminApiClient } from '@/lib/api/serverApiClient'
import { UsersClient } from './UsersClient'
import type { PlatformUser } from '../types'

export default async function SuperAdminUsersPage() {
  const response = await adminApiClient('/api/v1/super-admin/users')
  return <UsersClient initialUsers={(response.data || []) as PlatformUser[]} />
}
