export type UserRole = "owner" | "wife";

export type MessageRole = "user" | "assistant" | "system";

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role: UserRole;
}

export interface Conversation {
  id: string;
  title: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  model?: string | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";
export type FileType = "pdf" | "txt" | "docx" | "csv";

export interface BusinessDocument {
  id: string;
  filename: string;
  original_filename: string;
  file_type: FileType;
  file_size?: number | null;
  status: DocumentStatus;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryItem {
  id: string;
  key?: string | null;
  content: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export type ChatMode =
  | "chat"
  | "knowledge"
  | "research"
  | "marketing"
  | "personal";

export interface ChatDone {
  conversation_id: string;
  message_id: string;
  content: string;
  mode?: ChatMode | string;
  agents?: Array<{ id: string; name: string; title?: string }>;
  collaborative?: boolean;
}

export interface SpecialistAgentInfo {
  id: string;
  name: string;
  title: string;
  description: string;
  skills: string[];
  status: string;
  icon: string;
}

export interface ChatMeta {
  conversation_id: string;
  model: string;
  rag_chunks?: number;
  mode?: ChatMode | string;
  route_reason?: string;
  research_sources?: number;
  agents?: Array<{ id: string; name: string; title?: string }>;
  collaborative?: boolean;
}

export interface ChatProgress {
  step: string;
  detail: string;
  agent_id?: string;
  agent_name?: string;
}

export interface AutomationModuleInfo {
  id: string;
  title: string;
  description: string;
  example: string;
  status: string;
}

export interface AutomationItem {
  id: string;
  run_id: string;
  item_type: string;
  title: string;
  content: Record<string, unknown>;
  status: string;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface AutomationRun {
  id: string;
  module: string;
  title: string;
  prompt: string;
  status: string;
  plan_summary?: string | null;
  preview: Record<string, unknown>;
  result: Record<string, unknown>;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
  items: AutomationItem[];
}

export interface AutomationHistoryItem {
  id: string;
  module: string;
  title: string;
  prompt: string;
  status: string;
  plan_summary?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ChannelIdentity {
  id: string;
  user_id: string;
  channel: string;
  external_id: string;
  display_name?: string | null;
  allowed: boolean;
  is_owner: boolean;
  last_message_at?: string | null;
  created_at?: string | null;
}

export interface ChannelStatus {
  bridge_enabled: boolean;
  bridge_configured: boolean;
  gateway_online: boolean;
  whatsapp_linked: boolean;
  last_heartbeat_at?: string | null;
  last_message_at?: string | null;
  last_external_id?: string | null;
  default_agent: string;
  allowed_numbers: string[];
  identities: ChannelIdentity[];
  pairing_docs?: string;
}

