'use client'

import React, { useMemo, useState } from 'react'
import { Users } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { errorMessage } from '@/lib/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import { formatDateTime, type PlatformUser } from '../types'

export function UsersClient({ initialUsers }: { initialUsers: PlatformUser[] }) {
  const { showToast } = useToast()
  const [users, setUsers] = useState(initialUsers)
  const [query, setQuery] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return users
    return users.filter((user) =>
      user.email.toLowerCase().includes(q)
      || user.full_name.toLowerCase().includes(q)
      || user.role.toLowerCase().includes(q),
    )
  }, [users, query])

  async function reload() {
    const response = await apiClient('/api/v1/super-admin/users')
    setUsers(response.data || [])
  }

  async function toggleActive(user: PlatformUser) {
    setBusyId(user.id)
    try {
      await apiClient(`/api/v1/super-admin/users/${user.id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !user.is_active }),
      })
      await reload()
      showToast(user.is_active ? 'User deactivated' : 'User activated', 'success')
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to update user', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Users"
        description="Platform identities, store memberships, and account access."
      />
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search name or email"
        className="max-w-sm"
      />
      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Stores</TableHead>
              <TableHead>Last login</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-end">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-muted-foreground">
                  <Users className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No users found.
                </TableCell>
              </TableRow>
            )}
            {visible.map((user) => (
              <TableRow key={user.id} className="hover:bg-muted/50">
                <TableCell>
                  <div className="font-semibold">{user.full_name}</div>
                  <div className="text-sm text-muted-foreground">{user.email}</div>
                </TableCell>
                <TableCell>
                  <Badge variant={user.role === 'super_admin' ? 'default' : 'secondary'}>
                    {user.role === 'super_admin' ? 'Super admin' : 'User'}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {user.memberships.length === 0
                    ? '—'
                    : user.memberships.map((m) => `${m.tenant_name} (${m.role})`).join(', ')}
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDateTime(user.last_login_at)}</TableCell>
                <TableCell>
                  <Badge variant={user.is_active ? 'success' : 'destructive'}>
                    {user.is_active ? 'Active' : 'Disabled'}
                  </Badge>
                </TableCell>
                <TableCell className="text-end whitespace-nowrap">
                  {user.role === 'super_admin' ? (
                    <span className="text-xs text-muted-foreground">Protected</span>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={busyId === user.id}
                      onClick={() => toggleActive(user)}
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
