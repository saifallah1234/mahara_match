// Placement: frontend/src/lib/assistantConversations.ts
import type { Conversation } from '../api/assistant'

/** Most recent activity first; a conversation with no message yet sorts by its creation date. */
export function sortByActivity(conversations: Conversation[]): Conversation[] {
  const at = (item: Conversation) => +new Date(item.last_message_at ?? item.created_at)
  return [...conversations].sort((a, b) => at(b) - at(a))
}
