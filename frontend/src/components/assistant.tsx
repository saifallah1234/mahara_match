// Placement: frontend/src/components/assistant.tsx
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from './layout'
import { Button, ConfirmDialog, EmptyState, Panel, Textarea } from './ui'
import { Citations } from './domain'
import * as api from '../api/assistant'
import { sortByActivity } from '../lib/assistantConversations'
import { formatDate } from '../lib/format'

const EMPTY_HINT: Record<'CANDIDATE' | 'RECRUITER', string> = {
  CANDIDATE: 'Posez une question sur les offres, votre profil ou les formations.',
  RECRUITER: 'Demandez par exemple « candidats pour <offre> » ou une recherche libre de profils.',
}

// Static starters: clicking one only sends its text through the normal agent run.
const EXAMPLES: Record<'CANDIDATE' | 'RECRUITER', string[]> = {
  CANDIDATE: ['Quelles offres d’emploi me correspondent ?', 'Quelles formations pour mes compétences manquantes ?', 'Comment améliorer mon CV ?'],
  RECRUITER: ['Trouve des candidats en Python et SQL', 'Mes offres en Python'],
}

/** Assistant chat with its conversation list. basePath is the route prefix; the selected conversation id is the last segment. */
export function AssistantWorkspace({ basePath, role }: { basePath: string; role: 'CANDIDATE' | 'RECRUITER' }) {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<api.Conversation[]>([])
  const [messages, setMessages] = useState<api.ChatMessage[]>([])
  const [version, setVersion] = useState(0)
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<api.Conversation | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let live = true
    api.listConversations()
      .then((list) => { if (live) { setConversations(sortByActivity(list)); setError(null) } })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Historique indisponible.') })
    return () => { live = false }
  }, [version])

  // Drop the previous conversation's thread at once, so it never shows under the new one.
  useEffect(() => { setMessages([]) }, [conversationId])

  useEffect(() => {
    let live = true
    if (!conversationId) return
    api.listMessages(conversationId)
      .then((list) => { if (live) { setMessages(list); setError(null) } })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Historique indisponible.') })
    return () => { live = false }
  }, [conversationId, version])

  // The reply may arrive after the user has moved on; only follow it if they are still here.
  const selected = useRef(conversationId)
  useEffect(() => { selected.current = conversationId }, [conversationId])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, thinking])

  async function send(example?: string) {
    const text = (example ?? input).trim()
    if (!text || thinking) return
    const sentFrom = conversationId
    setInput(''); setError(null); setThinking(true)
    try {
      const result = await api.sendMessage(text, sentFrom)
      setVersion((current) => current + 1)
      if (result.conversation_id !== sentFrom && selected.current === sentFrom) navigate(`${basePath}/${result.conversation_id}`)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'L’assistant est indisponible pour le moment.')
    } finally {
      setThinking(false)
    }
  }

  async function remove(conversation: api.Conversation) {
    setError(null)
    try {
      await api.deleteConversation(conversation.id)
      if (conversation.id === conversationId) navigate(basePath)
      setVersion((current) => current + 1)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Suppression impossible.')
    }
  }

  return (
    <>
      <PageHeader title="Assistant" />
      <PageBody className="space-y-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[16rem_1fr]">
          <Panel title="Conversations" action={<Button size="sm" variant="secondaire" onClick={() => navigate(basePath)}>Nouvelle conversation</Button>}>
            {!conversations.length && <EmptyState title="Aucune conversation">Posez une question pour en commencer une.</EmptyState>}
            <ul className="divide-y divide-line">
              {conversations.map((item) => (
                <li key={item.id} className={`flex items-center justify-between gap-2 px-4 py-3 ${item.id === conversationId ? 'bg-mist' : ''}`}>
                  <Link to={`${basePath}/${item.id}`} className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-navy">{item.title || 'Conversation sans titre'}</span>
                    <span className="text-[12px] text-slate">{formatDate(item.last_message_at ?? item.created_at)}</span>
                  </Link>
                  <Button size="sm" variant="discret" onClick={() => setDeleting(item)}>Supprimer</Button>
                </li>
              ))}
            </ul>
          </Panel>
          {/* Fills the screen below the page header; only the thread scrolls, the input stays at the bottom. */}
          <div className="flex h-[calc(100dvh-8rem)] min-h-[26rem] flex-col gap-3">
            <Panel className="flex min-h-0 flex-1 flex-col">
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">
                {messages.length === 0 && !thinking && (
                  <div className="space-y-3">
                    <p className="text-[13.5px] text-slate">{EMPTY_HINT[role]}</p>
                    <div className="flex flex-wrap gap-2">
                      {EXAMPLES[role].map((example) => (
                        <Button key={example} size="sm" variant="secondaire" onClick={() => void send(example)}>{example}</Button>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map((m) => {
                  const mine = m.sender_type === 'USER'
                  return (
                    <div key={m.id} className={mine ? 'flex justify-end' : 'flex justify-start'}>
                      <div className={`max-w-[80%] rounded-[10px] px-4 py-2.5 text-[14px] ${mine ? 'bg-navy text-white' : 'bg-mist text-navy'}`}>
                        <p className="whitespace-pre-line">{m.content}</p>
                        {!mine && Array.isArray(m.citations_json) && <Citations items={m.citations_json} role={role} />}
                      </div>
                    </div>
                  )
                })}
                {thinking && <p className="text-[13px] text-slate">L’assistant réfléchit…</p>}
                <div ref={endRef} />
              </div>
            </Panel>
            {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
            <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); void send() }}>
              <Textarea
                aria-label="Votre question"
                rows={2}
                className="min-h-0! resize-none!"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send() } }}
                placeholder="Votre question… (Maj+Entrée pour aller à la ligne)"
              />
              <Button type="submit" disabled={thinking || !input.trim()}>Envoyer</Button>
            </form>
          </div>
        </div>
      </PageBody>
      {deleting && (
        <ConfirmDialog
          title="Supprimer cette conversation ?"
          danger
          onCancel={() => setDeleting(null)}
          onConfirm={() => { void remove(deleting); setDeleting(null) }}
        >
          « {deleting.title || 'Conversation sans titre'} » et ses messages seront supprimés.
        </ConfirmDialog>
      )}
    </>
  )
}
