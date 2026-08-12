'use client'

import { CSSProperties, ReactNode } from 'react'
import {
  DndContext, DragEndEvent, PointerSensor, closestCenter, useSensor, useSensors,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Pencil } from 'lucide-react'
import { useState } from 'react'
import { DispatchedAction, Section, StorePageSchema } from '@/lib/ai/types'
import { renderSections } from '@/components/storefront/PageRenderer'
import { resolveDesignVariantClasses } from '@/lib/design-tokens'
import { SectionPropertiesEditor } from './SectionPropertiesEditor'

type RenderOpts = { onAction?: (action: DispatchedAction) => void; tenantSlug?: string; showTypeLabels?: boolean; onAskAI?: (id: string, prompt: string) => void; onEditSection?: (id: string) => void }

function SortableSectionCard({ id, children, onEdit }: { id: string; children: ReactNode; onEdit: (id: string) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} className="relative group">
      <div className="absolute -left-3 -top-3 z-10 flex items-center gap-1 rounded-md bg-white/90 p-1 shadow-sm backdrop-blur border border-gray-200">
        <button
          type="button"
          className="cursor-grab p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 active:cursor-grabbing rounded"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 rounded"
          onClick={() => onEdit(id)}
          aria-label="Edit Properties"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
      {children}
    </div>
  )
}

function updateChildAt(sections: Section[], id: string, patch: Partial<Section>): Section[] {
  return sections.map((s) => (s.id === id ? { ...s, ...patch } : s))
}

/**
 * Reorders within its own list only — dragging a section from one list (e.g. the top level)
 * into a different list (e.g. a grid's children) isn't supported here, only reordering
 * within whichever list it already belongs to. Each list gets its own DndContext since
 * lists are fully independent (no cross-list drag interaction to coordinate).
 */
function DraggableSectionList({
  sections,
  onChange,
  opts,
  emptyLabel,
}: {
  sections: Section[]
  onChange: (next: Section[]) => void
  opts: RenderOpts
  emptyLabel?: string
}) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }))

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = sections.findIndex((s) => s.id === active.id)
    const newIndex = sections.findIndex((s) => s.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return
    onChange(arrayMove(sections, oldIndex, newIndex))
  }

  if (sections.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 p-4 text-center text-sm text-gray-400">
        {emptyLabel ?? 'No sections yet.'}
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-4 pl-7">
          {sections.map((section) => (
            <SortableSectionCard 
              key={section.id} 
              id={section.id}
              onEdit={(id) => opts.onEditSection?.(id)}
            >
              {section.type === 'grid_container' ? (
                <GridContainerEditor
                  section={section}
                  onChange={(patch) => onChange(updateChildAt(sections, section.id, patch))}
                  opts={opts}
                />
              ) : section.type === 'two_column_layout' ? (
                <TwoColumnLayoutEditor
                  section={section}
                  onChange={(patch) => onChange(updateChildAt(sections, section.id, patch))}
                  opts={opts}
                />
              ) : (
                renderSections([section], opts)[0]
              )}
            </SortableSectionCard>
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}

function GridContainerEditor({
  section, onChange, opts,
}: { section: Section; onChange: (patch: Partial<Section>) => void; opts: RenderOpts }) {
  const containerClass = resolveDesignVariantClasses(section.settings.design_variant)
  return (
    <div className={containerClass}>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-current/60">
        Grid ({section.settings.columns ?? 3} columns)
      </div>
      <DraggableSectionList
        sections={section.children ?? []}
        onChange={(children) => onChange({ children })}
        opts={opts}
        emptyLabel="Empty grid — add items via the AI chat."
      />
    </div>
  )
}

function TwoColumnLayoutEditor({
  section, onChange, opts,
}: { section: Section; onChange: (patch: Partial<Section>) => void; opts: RenderOpts }) {
  const containerClass = resolveDesignVariantClasses(section.settings.design_variant)
  const zones = section.zones ?? {}
  return (
    <div className={containerClass}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-current/60">Left</div>
          <DraggableSectionList
            sections={zones.left ?? []}
            onChange={(left) => onChange({ zones: { ...zones, left } })}
            opts={opts}
            emptyLabel="Empty — left column."
          />
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-current/60">Right</div>
          <DraggableSectionList
            sections={zones.right ?? []}
            onChange={(right) => onChange({ zones: { ...zones, right } })}
            opts={opts}
            emptyLabel="Empty — right column."
          />
        </div>
      </div>
    </div>
  )
}

export function DraggablePageEditor({
  page,
  onChange,
  onSave,
  saving,
  onAction,
  tenantSlug,
  showTypeLabels = false,
  onAskAI,
}: {
  page: StorePageSchema | null
  /** Called with the full, reordered top-level sections array — the caller owns persistence timing. */
  onChange: (sections: Section[]) => void
  onSave: () => void
  saving: boolean
  onAction?: (action: DispatchedAction) => void
  tenantSlug?: string
  showTypeLabels?: boolean
  onAskAI?: (id: string, prompt: string) => void
}) {
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null)

  if (!page) {
    return <div className="p-8 text-center text-gray-400">Loading page…</div>
  }

  // Find the currently edited section recursively
  const findSection = (sections: Section[], id: string): Section | undefined => {
    for (const sec of sections) {
      if (sec.id === id) return sec
      if (sec.children) {
        const found = findSection(sec.children, id)
        if (found) return found
      }
      if (sec.zones) {
        for (const zone of Object.values(sec.zones)) {
          if (zone) {
            const found = findSection(zone, id)
            if (found) return found
          }
        }
      }
    }
    return undefined
  }

  const editingSection = editingSectionId ? findSection(page.sections, editingSectionId) : null

  // Update a nested section
  const patchSectionRecursively = (sections: Section[], id: string, patch: Partial<Section>): Section[] => {
    return sections.map((sec) => {
      if (sec.id === id) {
        return { ...sec, ...patch }
      }
      if (sec.children) {
        return { ...sec, children: patchSectionRecursively(sec.children, id, patch) }
      }
      if (sec.zones) {
        const newZones: any = {}
        for (const [zoneName, zoneSections] of Object.entries(sec.zones)) {
          if (zoneSections) {
            newZones[zoneName] = patchSectionRecursively(zoneSections, id, patch)
          }
        }
        return { ...sec, zones: newZones }
      }
      return sec
    })
  }

  const handleSectionPatch = (patch: Partial<Section>) => {
    if (!editingSectionId) return
    onChange(patchSectionRecursively(page.sections, editingSectionId, patch))
  }

  return (
    <div className="flex w-full h-[calc(100vh-100px)]">
      <div className="flex-1 overflow-y-auto px-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400">Use the toolbar on the left of each section to reorder or edit.</p>
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save Layout'}
            </button>
          </div>
          <DraggableSectionList 
            sections={page.sections} 
            onChange={onChange} 
            opts={{ 
              onAction, 
              tenantSlug, 
              showTypeLabels, 
              onEditSection: (id) => setEditingSectionId(id) 
            }} 
          />
        </div>
      </div>
      
      {editingSection && (
        <div className="w-[350px] shrink-0 border-l border-gray-200">
          <SectionPropertiesEditor
            section={editingSection}
            onChange={handleSectionPatch}
            onClose={() => setEditingSectionId(null)}
            onAskAI={(id, prompt) => {
              if (onAskAI) onAskAI(id, prompt)
            }}
          />
        </div>
      )}
    </div>
  )
}
