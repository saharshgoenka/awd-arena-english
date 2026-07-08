import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Key, Menu, Save, X } from 'lucide-react'

const OPENROUTER_KEY_STORAGE = 'OPENROUTER_API_KEY'
const REFEREE_KEY_STORAGE = 'REFEREE_API_KEY'

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const loc = useLocation()
  const active = (path: string) => loc.pathname.startsWith(path)

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [openRouterKey, setOpenRouterKey] = useState('')
  const [refereeKey, setRefereeKey] = useState('')

  useEffect(() => {
    setOpenRouterKey(localStorage.getItem(OPENROUTER_KEY_STORAGE) || '')
    setRefereeKey(localStorage.getItem(REFEREE_KEY_STORAGE) || '')

    const openDrawer = () => setDrawerOpen(true)
    window.addEventListener('openclaw:open-api-key-drawer', openDrawer)
    return () => window.removeEventListener('openclaw:open-api-key-drawer', openDrawer)
  }, [])

  const saveKeys = () => {
    const trimmedOpenRouter = openRouterKey.trim()
    const trimmedReferee = refereeKey.trim()

    if (trimmedOpenRouter) {
      localStorage.setItem(OPENROUTER_KEY_STORAGE, trimmedOpenRouter)
    } else {
      localStorage.removeItem(OPENROUTER_KEY_STORAGE)
    }

    if (trimmedReferee) {
      localStorage.setItem(REFEREE_KEY_STORAGE, trimmedReferee)
    } else {
      localStorage.removeItem(REFEREE_KEY_STORAGE)
    }

    window.dispatchEvent(new Event('openclaw:openrouter-key-updated'))
    setDrawerOpen(false)
  }

  const openRouterSaved = Boolean(localStorage.getItem(OPENROUTER_KEY_STORAGE))

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-30 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3">
          <nav className="flex items-center gap-2">
            <Link
              to="/config"
              className={`rounded-md px-3 py-2 text-sm font-medium transition ${active('/config') ? 'bg-cyan-500 text-zinc-950' : 'text-zinc-300 hover:bg-zinc-800 hover:text-white'}`}
            >
              Setup
            </Link>
            <Link
              to="/history"
              className={`rounded-md px-3 py-2 text-sm font-medium transition ${active('/history') ? 'bg-cyan-500 text-zinc-950' : 'text-zinc-300 hover:bg-zinc-800 hover:text-white'}`}
            >
              History
            </Link>
          </nav>

          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100 transition hover:border-cyan-400 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            aria-label="Open API key settings"
          >
            <Key className="h-4 w-4" />
            <span className="hidden sm:inline">{openRouterSaved ? 'Key saved' : 'Add key'}</span>
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-6">{children}</main>

      {drawerOpen && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close API key settings"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col border-l border-zinc-800 bg-zinc-950 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-cyan-400 text-zinc-950">
                  <Menu className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-base font-semibold">API keys</h2>
                  <p className="text-sm text-zinc-400">Saved in this browser until you replace them.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-md p-2 text-zinc-400 transition hover:bg-zinc-900 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
                aria-label="Close API key settings"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-zinc-200">OpenRouter API key</span>
                <input
                  type="password"
                  value={openRouterKey}
                  onChange={(event) => setOpenRouterKey(event.target.value)}
                  placeholder="sk-or-v1-..."
                  className="h-11 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                />
                <span className="block text-xs leading-5 text-zinc-500">
                  This is the model-provider key used when starting matches. Replace it here after billing or rate-limit failures.
                </span>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-zinc-200">Referee API key</span>
                <input
                  type="password"
                  value={refereeKey}
                  onChange={(event) => setRefereeKey(event.target.value)}
                  placeholder="Only needed if referee auth is enabled"
                  className="h-11 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                />
              </label>
            </div>

            <div className="border-t border-zinc-800 p-5">
              <button
                type="button"
                onClick={saveKeys}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-cyan-400 px-4 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              >
                <Save className="h-4 w-4" />
                Save keys
              </button>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}

export default Layout
