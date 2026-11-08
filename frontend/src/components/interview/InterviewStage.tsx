// Placement: frontend/src/components/interview/InterviewStage.tsx
import type { ReactNode } from 'react'

// Shared by the interviewer avatar and the candidate camera so both frames keep the same height.
export const STAGE_FRAME = 'h-[520px] max-h-[75vh] rounded-xl bg-navy object-cover'
export const INTERVIEWER_FRAME = `${STAGE_FRAME} aspect-[9/16] w-auto`

export function ActionBar({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-3">{children}</div>
}

export function InterviewStage({ interviewer, candidate, actions }: { interviewer: ReactNode; candidate: ReactNode; actions: ReactNode }) {
  return <div className="space-y-4">
    <div className="flex flex-col items-center gap-4 md:flex-row md:items-start">
      <section aria-label="Recruteur virtuel" className="w-min max-w-full shrink-0">{interviewer}</section>
      <section aria-label="Vous" className="w-full min-w-0 flex-1 space-y-2">{candidate}</section>
    </div>
    <ActionBar>{actions}</ActionBar>
  </div>
}

export function CameraIdle({ children = 'Votre caméra s’activera quand ce sera à vous de répondre.' }: { children?: ReactNode }) {
  return <div className={`${STAGE_FRAME} flex w-full items-center justify-center p-6 text-center text-sm text-white/80`}>{children}</div>
}
