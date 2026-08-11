export type SectionType =
  | 'hero_banner'
  | 'product_grid'
  | 'video_embed'
  | 'text_block'
  | 'gallery'
  | 'button_group'
  | 'table'

export type PageType = 'static_page' | 'template'

export type ButtonVariant = 'primary' | 'secondary' | 'outline'
export type ButtonActionType = 'NAVIGATE' | 'OPEN_MODAL' | 'ADD_TO_CART' | 'APPLY_COUPON'

export interface ButtonSpec {
  label: string
  variant?: ButtonVariant
  actionType: ButtonActionType
  actionPayload?: Record<string, any>
}

export interface SectionMedia {
  type: 'image' | 'video'
  url: string
  aspect_ratio?: string
}

export interface Section {
  id: string
  type: SectionType
  settings: Record<string, any>
  media?: SectionMedia
}

export interface StorePageSchema {
  page_key: string
  page_type: PageType
  title: string
  sections: Section[]
  /** Page-level theme — distinct from any single section's own settings.background_color. */
  background_color?: string | null
  text_color?: string | null
  /** True if the draft has edits the store owner hasn't published yet. Only meaningful on the admin/draft view. */
  has_unpublished_changes?: boolean
  published_at?: string | null
}

export interface StorePageSummary {
  page_key: string
  page_type: PageType
  title: string
  section_count: number
}

export interface ToolCallRecord {
  name: string
  input: unknown
  output: unknown
  is_error: boolean
}

export interface AIChatResponse {
  reply: string
  tool_calls: ToolCallRecord[]
  used_provider: 'gemini' | 'mock'
  page: StorePageSchema | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  toolCalls?: ToolCallRecord[]
}

export interface DispatchedAction {
  label: string
  actionType: ButtonActionType
  actionPayload?: Record<string, any>
}

export interface StorePageVersionSummary {
  id: number
  created_at: string
  title: string
  section_count: number
}

export interface ChatMessageRecord {
  role: 'user' | 'assistant'
  text: string
  tool_calls?: ToolCallRecord[] | null
}

export interface ConversationResponse {
  messages: ChatMessageRecord[]
}
