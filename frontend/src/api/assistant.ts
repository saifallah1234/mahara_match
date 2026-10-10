import { allPages } from './auth.ts'
import { request } from './client.ts'

export type ChatMessage = {
  id: string; conversation_id: string; sender_type: string; content: string
  citations_json: { label: string; reference: string }[] | null; created_at: string
}
export type Conversation = { id: string; title: string; last_message_at: string | null; created_at: string }
export type AgentReply = { conversation_id: string; execution_id: string; message_id: string | null; reply: string | null; error_code: string | null }

export const listConversations = () => allPages<Conversation>('/conversations/')
export const listMessages = (conversationId: string) => allPages<ChatMessage>(`/conversations/${conversationId}/messages/`)
export const sendMessage = (message: string, conversationId?: string) =>
  request<AgentReply>('/agent-runs/', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId }) })