import { create } from 'zustand'

type SessionStore = {
  token: string | null
  setToken: (token: string) => void
}

export const useSessionStore = create<SessionStore>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
}))
