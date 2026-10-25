'use client'

import React, { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

type PasswordInputProps = Omit<React.ComponentProps<'input'>, 'type'> & {
  showLabel?: string
  hideLabel?: string
}

/** Password field with a show/hide toggle. Always LTR so Latin passwords don't reorder in RTL pages. */
export function PasswordInput({
  className = '',
  showLabel = 'הצגת סיסמה',
  hideLabel = 'הסתרת סיסמה',
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <input {...props} dir="ltr" type={visible ? 'text' : 'password'} className={`${className} pe-9 text-start`} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? hideLabel : showLabel}
        aria-pressed={visible}
        className="absolute inset-y-0 end-0 flex w-9 items-center justify-center text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
      </button>
    </div>
  )
}
