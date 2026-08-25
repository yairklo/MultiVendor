'use client'

import { createContext, PointerEvent, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Maximize2, Minus, Plus, UnfoldHorizontal } from 'lucide-react'
import { useUiLocale } from '@/context/UiLocaleContext'
import { Section } from '@/lib/ai/types'
import { SectionPropertiesEditor } from './SectionPropertiesEditor'

const CANVAS_WIDTH = 1280
const ZOOM_STEPS = [0.5, 0.75, 1] as const

type ZoomMode = 'fit' | 'fit-width' | number

export type PreviewPropertiesSession = {
  section: Section
  onChange: (patch: Partial<Section>) => void
  onClose: () => void
  onAskAI?: (id: string, prompt: string) => void
}

type PreviewChrome = {
  setPropertiesSession: (session: PreviewPropertiesSession | null) => void
}

const PreviewChromeContext = createContext<PreviewChrome | null>(null)

export function usePreviewChrome() {
  return useContext(PreviewChromeContext)
}

function numericZoom(mode: ZoomMode, currentScale: number) {
  return typeof mode === 'number' ? mode : currentScale
}

export function PreviewCanvas({ children }: { children: ReactNode }) {
  const { t } = useUiLocale()
  const viewportRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const panningRef = useRef(false)
  const lastPointerRef = useRef({ x: 0, y: 0 })
  const [mode, setMode] = useState<ZoomMode>('fit-width')
  const [scale, setScale] = useState(1)
  const [contentHeight, setContentHeight] = useState(900)
  const [reduceMotion, setReduceMotion] = useState(false)
  const [propertiesSession, setPropertiesSession] = useState<PreviewPropertiesSession | null>(null)
  const setPropertiesSessionRef = useRef(setPropertiesSession)
  setPropertiesSessionRef.current = setPropertiesSession
  const chrome = useMemo<PreviewChrome>(() => ({
    setPropertiesSession: (session) => setPropertiesSessionRef.current(session),
  }), [])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduceMotion(mq.matches)
    const onChange = () => setReduceMotion(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const recompute = useCallback(() => {
    const vp = viewportRef.current
    const content = contentRef.current
    if (!vp || !content) return
    const height = Math.max(content.scrollHeight, 400)
    setContentHeight(height)
    const pad = 24
    const sx = (vp.clientWidth - pad) / CANVAS_WIDTH
    const sy = (vp.clientHeight - pad) / height
    if (mode === 'fit') {
      setScale(Math.max(0.15, Math.min(sx, sy, 1)))
    } else if (mode === 'fit-width') {
      setScale(Math.max(0.15, Math.min(sx, 1)))
    } else {
      setScale(mode)
    }
  }, [mode])

  useLayoutEffect(() => {
    recompute()
    const vp = viewportRef.current
    const content = contentRef.current
    if (!vp || !content || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => recompute())
    ro.observe(vp)
    ro.observe(content)
    return () => ro.disconnect()
  }, [recompute, children])

  useEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const onWheel = (e: globalThis.WheelEvent) => {
      if (!e.shiftKey) return
      e.preventDefault()
      el.scrollLeft += e.deltaY + e.deltaX
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  function canPanFromTarget(target: EventTarget | null, button: number) {
    if (button === 1) return true
    if (button !== 0) return false
    if (!contentRef.current || !target) return true
    return !contentRef.current.contains(target as Node)
  }

  function handlePointerDown(e: PointerEvent<HTMLDivElement>) {
    if (e.button === 1) e.preventDefault()
    if (!canPanFromTarget(e.target, e.button)) return
    panningRef.current = true
    lastPointerRef.current = { x: e.clientX, y: e.clientY }
    viewportRef.current?.setPointerCapture(e.pointerId)
  }

  function handlePointerMove(e: PointerEvent<HTMLDivElement>) {
    if (!panningRef.current || !viewportRef.current) return
    const dx = e.clientX - lastPointerRef.current.x
    const dy = e.clientY - lastPointerRef.current.y
    lastPointerRef.current = { x: e.clientX, y: e.clientY }
    viewportRef.current.scrollLeft -= dx
    viewportRef.current.scrollTop -= dy
  }

  function handlePointerUp(e: PointerEvent<HTMLDivElement>) {
    panningRef.current = false
    if (viewportRef.current?.hasPointerCapture(e.pointerId)) {
      viewportRef.current.releasePointerCapture(e.pointerId)
    }
  }

  const scaledW = CANVAS_WIDTH * scale
  const scaledH = contentHeight * scale
  const isFit = mode === 'fit'
  const isFitWidth = mode === 'fit-width'

  function modeButtonClass(active: boolean) {
    return `flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98] ${
      active
        ? 'bg-primary text-primary-foreground shadow-sm'
        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
    }`
  }

  return (
    <PreviewChromeContext.Provider value={chrome}>
    <div dir="ltr" className="flex min-h-0 min-w-0 flex-1">
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-card/80 px-3 py-2 backdrop-blur-sm">
        <p className="text-xs text-muted-foreground">{t('aiLayout.previewHint')}</p>
        <div className="flex items-center gap-1 rounded-lg border border-border bg-background p-0.5">
          <button
            type="button"
            onClick={() => setMode('fit')}
            aria-pressed={isFit}
            className={modeButtonClass(isFit)}
          >
            <Maximize2 className="h-3.5 w-3.5" />
            {t('aiLayout.previewFit')}
          </button>
          <button
            type="button"
            onClick={() => setMode('fit-width')}
            aria-pressed={isFitWidth}
            className={modeButtonClass(isFitWidth)}
          >
            <UnfoldHorizontal className="h-3.5 w-3.5" />
            {t('aiLayout.previewFitWidth')}
          </button>
          <button
            type="button"
            onClick={() => setMode((prev) => {
              const next = ZOOM_STEPS.filter((s) => s < numericZoom(prev, scale) - 0.01).pop() ?? 0.5
              return next
            })}
            aria-label={t('aiLayout.previewZoomOut')}
            className="rounded-md p-1.5 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          {ZOOM_STEPS.map((step) => (
            <button
              key={step}
              type="button"
              onClick={() => setMode(step)}
              aria-pressed={mode === step}
              className={`rounded-md px-2 py-1.5 text-xs font-medium tabular-nums transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98] ${
                mode === step
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              {Math.round(step * 100)}%
            </button>
          ))}
          <button
            type="button"
            onClick={() => setMode((prev) => {
              const next = ZOOM_STEPS.find((s) => s > numericZoom(prev, scale) + 0.01) ?? 1
              return next
            })}
            aria-label={t('aiLayout.previewZoomIn')}
            className="rounded-md p-1.5 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div
        ref={viewportRef}
        dir="ltr"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        className="preview-canvas-scroll min-h-0 flex-1 overflow-scroll overscroll-contain bg-[radial-gradient(circle_at_1px_1px,var(--border)_1px,transparent_0)] bg-[size:16px_16px]"
      >
        <div
          className={`flex cursor-grab active:cursor-grabbing ${isFit ? 'h-full min-h-full items-center justify-center p-3' : 'p-4'}`}
          style={isFit ? undefined : { minWidth: scaledW + 32, minHeight: scaledH + 32 }}
        >
          <div
            className="relative shrink-0 cursor-auto overflow-hidden rounded-lg border border-border bg-background shadow-xl"
            style={{ width: scaledW, height: scaledH }}
          >
            <div
              ref={contentRef}
              className={reduceMotion ? undefined : 'origin-top-left'}
              style={{
                width: CANVAS_WIDTH,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
                transition: reduceMotion ? undefined : 'transform 200ms cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            >
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
      {propertiesSession && (
        <aside className="relative z-20 flex min-h-0 w-[22rem] shrink-0 flex-col overflow-hidden border-s border-border bg-card shadow-lg pointer-events-auto">
          <SectionPropertiesEditor
            section={propertiesSession.section}
            onChange={propertiesSession.onChange}
            onClose={propertiesSession.onClose}
            onAskAI={propertiesSession.onAskAI}
          />
        </aside>
      )}
    </div>
    </PreviewChromeContext.Provider>
  )
}
