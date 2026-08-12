import sys
path = "frontend/src/components/admin/ai/DraggablePageEditor.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_imports = '''import { CSSProperties, ReactNode } from 'react'
import {
  DndContext, DragEndEvent, PointerSensor, closestCenter, useSensor, useSensors,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import { DispatchedAction, Section, StorePageSchema } from '@/lib/ai/types''''

new_imports = '''import { CSSProperties, ReactNode, useState } from 'react'
import {
  DndContext, DragEndEvent, PointerSensor, closestCenter, useSensor, useSensors,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Pencil, X } from 'lucide-react'
import { DispatchedAction, Section, StorePageSchema } from '@/lib/ai/types''''
content = content.replace(old_imports, new_imports)

old_card = '''function SortableSectionCard({ id, children }: { id: string; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} className="group relative">
      <button
        type="button"
        className="absolute -left-7 top-1/2 hidden -translate-y-1/2 cursor-grab items-center rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 group-hover:flex active:cursor-grabbing"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      {children}
    </div>
  )
}'''
new_card = '''function SortableSectionCard({ section, onChange, children }: { section: Section; onChange: (patch: Partial<Section>) => void; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: section.id })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const [isEditing, setIsEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(section.content?.title || section.content?.text || '')
  const [draftVariant, setDraftVariant] = useState(section.settings?.design_variant || 'default')

  function handleSave() {
    onChange({
      content: { ...section.content, title: draftTitle, text: section.content?.text ? draftTitle : undefined },
      settings: { ...section.settings, design_variant: draftVariant }
    })
    setIsEditing(false)
  }

  return (
    <div ref={setNodeRef} style={style} className="group relative -ml-7 pl-7">
      <div className="absolute left-0 top-1/2 hidden -translate-y-1/2 flex-col gap-1 rounded bg-white p-1 shadow-sm border border-gray-200 group-hover:flex z-10">
        <button
          type="button"
          className="cursor-grab items-center rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 active:cursor-grabbing"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="items-center rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          onClick={() => setIsEditing(true)}
          aria-label="Edit section"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>

      {isEditing && (
        <div className="absolute z-20 top-0 left-8 w-64 rounded-lg bg-white p-4 shadow-lg border border-gray-200">
           <div className="flex justify-between items-center mb-3">
             <h4 className="text-sm font-semibold text-gray-900">Edit Section</h4>
             <button onClick={() => setIsEditing(false)}><X className="h-4 w-4 text-gray-400 hover:text-gray-700" /></button>
           </div>
           <div className="mb-3 space-y-2">
             <label className="block text-xs font-medium text-gray-700">Text / Title</label>
             <input type="text" value={draftTitle} onChange={e => setDraftTitle(e.target.value)} className="w-full rounded border px-2 py-1 text-sm text-gray-900" />
           </div>
           <div className="mb-4 space-y-2">
             <label className="block text-xs font-medium text-gray-700">Design Variant</label>
             <select value={draftVariant} onChange={e => setDraftVariant(e.target.value)} className="w-full rounded border px-2 py-1 text-sm text-gray-900">
               <option value="default">Default</option>
               <option value="dark">Dark</option>
               <option value="light">Light</option>
               <option value="primary">Primary</option>
               <option value="hero">Hero</option>
             </select>
           </div>
           <div className="flex justify-end">
             <button onClick={handleSave} className="rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">Save</button>
           </div>
        </div>
      )}

      {children}
    </div>
  )
}'''
content = content.replace(old_card, new_card)

old_map = '''          {sections.map((section) => (
            <SortableSectionCard key={section.id} id={section.id}>
              {section.type === 'grid_container' ? ('''
new_map = '''          {sections.map((section) => (
            <SortableSectionCard 
              key={section.id} 
              section={section}
              onChange={(patch) => onChange(updateChildAt(sections, section.id, patch))}
            >
              {section.type === 'grid_container' ? ('''
content = content.replace(old_map, new_map)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched successfully")
