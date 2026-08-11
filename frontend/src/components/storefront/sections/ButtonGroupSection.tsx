import { CSSProperties } from 'react'
import { ButtonSpec, DispatchedAction, Section } from '@/lib/ai/types'

const VARIANT_CLASSES: Record<string, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
  outline: 'border border-gray-300 text-gray-900 hover:bg-gray-50',
}

export function ButtonGroupSection({
  section,
  themeStyle,
  onAction,
}: {
  section: Section
  themeStyle: CSSProperties
  onAction?: (action: DispatchedAction) => void
}) {
  const buttons: ButtonSpec[] = Array.isArray(section.settings.buttons) ? section.settings.buttons : []

  return (
    <div className="rounded-2xl p-6" style={{ ...themeStyle, background: 'var(--section-bg, #ffffff)' }}>
      {buttons.length === 0 && <span className="text-sm text-gray-400">No buttons configured.</span>}
      <div className="flex flex-wrap gap-3">
        {buttons.map((button, i) => (
          <button
            key={i}
            type="button"
            className={`rounded-full px-5 py-2 text-sm font-semibold transition-colors ${VARIANT_CLASSES[button.variant ?? 'primary']}`}
            onClick={() =>
              // Only ever dispatches a structured {actionType, actionPayload} record —
              // never evaluates or executes anything the AI wrote.
              onAction?.({ label: button.label, actionType: button.actionType, actionPayload: button.actionPayload })
            }
          >
            {button.label}
          </button>
        ))}
      </div>
    </div>
  )
}
