import { useEffect, useRef, useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, Input, Panel } from '../../components/ui'
import { Citations } from '../../components/domain'
import * as api from '../../api/assistant'

export default function CandidatAssistant() {
  const [conversationId, setConversationId] = useState<string>()
  const [messages, setMessages] = useState<api.ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  // Reprend la conversation la plus récente, s'il y en a une.
  useEffect(() => {
    api.listConversations().then(async (list) => {
      const last = [...list].sort((a, b) => +new Date(b.last_message_at ?? b.created_at) - +new Date(a.last_message_at ?? a.created_at))[0]
      if (!last) return
      setConversationId(last.id)
      setMessages(await api.listMessages(last.id))
    }).catch(() => {})
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, thinking])

  async function send() {
    const text = input.trim()
    if (!text || thinking) return
    setInput(''); setError(null); setThinking(true)
    try {
      const result = await api.sendMessage(text, conversationId)
      setConversationId(result.conversation_id)
      setMessages(await api.listMessages(result.conversation_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'L’assistant est indisponible pour le moment.')
    } finally {
      setThinking(false)
    }
  }

  return (
    <>
      <PageHeader title="Assistant" />
      <PageBody className="space-y-4">
        <Panel>
          <div className="max-h-[60vh] min-h-64 space-y-3 overflow-y-auto p-5">
            {messages.length === 0 && !thinking && (
              <p className="text-[13.5px] text-slate">Posez une question sur les offres, votre profil ou les formations.</p>
            )}
            {messages.map((m) => {
              const mine = m.sender_type === 'USER'
              return (
                <div key={m.id} className={mine ? 'flex justify-end' : 'flex justify-start'}>
                  <div className={`max-w-[80%] rounded-[10px] px-4 py-2.5 text-[14px] ${mine ? 'bg-navy text-white' : 'bg-mist text-navy'}`}>
                    <p className="whitespace-pre-line">{m.content}</p>
                    {!mine && Array.isArray(m.citations_json) && <Citations items={m.citations_json} />}
                  </div>
                </div>
              )
            })}
            {thinking && <p className="text-[13px] text-slate">L’assistant réfléchit…</p>}
            <div ref={endRef} />
          </div>
        </Panel>
        {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void send() }}>
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Votre question…" />
          <Button type="submit" disabled={thinking || !input.trim()}>Envoyer</Button>
        </form>
      </PageBody>
    </>
  )
}