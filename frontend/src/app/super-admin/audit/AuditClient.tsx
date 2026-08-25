'use client'

import React, { useMemo, useState } from 'react'
import { ScrollText } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import { formatDateTime, type AuditLogItem } from '../types'

export function AuditClient({ initialLogs }: { initialLogs: AuditLogItem[] }) {
  const [query, setQuery] = useState('')
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return initialLogs
    return initialLogs.filter((log) =>
      log.action.toLowerCase().includes(q)
      || log.resource.toLowerCase().includes(q)
      || JSON.stringify(log.details_json || {}).toLowerCase().includes(q),
    )
  }, [initialLogs, query])

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Audit log"
        description="Platform actions: store status, plans, marketplace listing, and user access."
      />
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search action or resource"
        className="max-w-sm"
      />
      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>When</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-12 text-center text-muted-foreground">
                  <ScrollText className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No audit events yet. Suspend a store or change a plan to write the first entry.
                </TableCell>
              </TableRow>
            )}
            {visible.map((log) => (
              <TableRow key={log.id} className="hover:bg-muted/50">
                <TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                <TableCell className="font-medium">{log.action}</TableCell>
                <TableCell className="font-mono text-xs">{log.resource}</TableCell>
                <TableCell className="text-muted-foreground">{log.actor_name || log.actor_email || (log.user_id ? `User #${log.user_id}` : '—')}</TableCell>
                <TableCell className="max-w-xs truncate font-mono text-xs text-muted-foreground">
                  {log.details_json ? JSON.stringify(log.details_json) : '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
