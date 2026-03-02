import { create } from 'zustand'

export type LayoutPreset = 'balanced' | 'focus_timeline' | 'focus_details'

type LayoutStore = {
  panelLayout: LayoutPreset
  compactNav: boolean
  setPanelLayout: (layout: LayoutPreset) => void
  setCompactNav: (value: boolean) => void
  hydrate: () => void
}

const STORAGE_KEY = 'openeinstein-layout'

export const useLayoutStore = create<LayoutStore>((set, get) => ({
  panelLayout: 'balanced',
  compactNav: false,
  setPanelLayout: (panelLayout) => {
    set({ panelLayout })
    const next = { ...get(), panelLayout }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ panelLayout: next.panelLayout, compactNav: next.compactNav }),
    )
  },
  setCompactNav: (compactNav) => {
    set({ compactNav })
    const next = { ...get(), compactNav }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ panelLayout: next.panelLayout, compactNav: next.compactNav }),
    )
  },
  hydrate: () => {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return
    }
    try {
      const parsed = JSON.parse(raw) as { panelLayout?: LayoutPreset; compactNav?: boolean }
      set({
        panelLayout: parsed.panelLayout ?? 'balanced',
        compactNav: parsed.compactNav ?? false,
      })
    } catch {
      set({ panelLayout: 'balanced', compactNav: false })
    }
  },
}))
