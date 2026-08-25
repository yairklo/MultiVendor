import { adminApiClient } from '@/lib/api/serverApiClient'
import { AuditClient } from './AuditClient'
import type { AuditLogItem } from '../types'

export default async function SuperAdminAuditPage() {
  const response = await adminApiClient('/api/v1/super-admin/audit-logs')
  return <AuditClient initialLogs={(response.data || []) as AuditLogItem[]} />
}
