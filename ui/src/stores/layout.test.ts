import { beforeEach, describe, expect, it } from 'vitest'

import { useLayoutStore } from './layout'

describe('layout store', () => {
  beforeEach(() => {
    localStorage.clear()
    useLayoutStore.setState({ panelLayout: 'balanced', compactNav: false })
  })

  it('persists and hydrates layout preferences', () => {
    useLayoutStore.getState().setPanelLayout('focus_timeline')
    useLayoutStore.getState().setCompactNav(true)

    useLayoutStore.setState({ panelLayout: 'balanced', compactNav: false })
    useLayoutStore.getState().hydrate()

    const state = useLayoutStore.getState()
    expect(state.panelLayout).toBe('focus_timeline')
    expect(state.compactNav).toBe(true)
  })
})
