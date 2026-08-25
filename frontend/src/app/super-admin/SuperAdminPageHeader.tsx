import React from 'react'

export function SuperAdminPageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description: string
  actions?: React.ReactNode
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      {actions}
    </div>
  )
}
