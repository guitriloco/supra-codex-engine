import { useEffect, useState } from 'react'
import { Card, CardHeader } from '@/components/Card'
import { Button } from '@/components/Button'
import {
  ShoppingCart,
  Star,
  Download,
  Search,
  Filter,
  Check,
  Loader2,
  Package,
  ExternalLink,
} from 'lucide-react'
import {
  listMarketplaceModules,
  installModule,
  uninstallModule,
  listInstalledModules,
  MarketplaceModule,
  ApiError,
} from '@/services/api'

const categories = ['All', 'Scraping', 'Leads', 'Analysis', 'SEO', 'Enrichment']

type ViewMode = 'browse' | 'installed'

export default function Marketplace() {
  const [modules, setModules] = useState<MarketplaceModule[]>([])
  const [installedIds, setInstalledIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('All')
  const [viewMode, setViewMode] = useState<ViewMode>('browse')
  const [installingId, setInstallingId] = useState<string | null>(null)

  async function loadData() {
    try {
      setLoading(true)
      setError(null)
      const [allModules, installed] = await Promise.all([
        listMarketplaceModules(),
        listInstalledModules(),
      ])
      setModules(allModules)
      setInstalledIds(new Set(installed.map((m) => m.id)))
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API Error: ${err.message}`)
      } else {
        setError('Failed to load marketplace modules. Is the API server running?')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  async function handleInstallToggle(moduleId: string, currentlyInstalled: boolean) {
    setInstallingId(moduleId)
    try {
      if (currentlyInstalled) {
        await uninstallModule(moduleId)
        setInstalledIds((prev) => {
          const next = new Set(prev)
          next.delete(moduleId)
          return next
        })
      } else {
        await installModule(moduleId)
        setInstalledIds((prev) => new Set(prev).add(moduleId))
      }
    } catch (err) {
      console.error('Install toggle failed:', err)
    } finally {
      setInstallingId(null)
    }
  }

  // Filter modules
  const displayedModules = modules.filter((mod) => {
    // View mode filter
    if (viewMode === 'installed' && !installedIds.has(mod.id)) return false

    // Category filter
    if (activeCategory !== 'All' && mod.category !== activeCategory) return false

    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (
        mod.name.toLowerCase().includes(q) ||
        mod.description.toLowerCase().includes(q) ||
        mod.author.toLowerCase().includes(q)
      )
    }

    return true
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Nectar Marketplace</h1>
          <p className="text-sm text-surface-500 mt-1">
            {viewMode === 'browse'
              ? 'Discover and install automation modules'
              : `Your installed modules (${installedIds.size})`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {viewMode === 'browse' ? (
            <Button variant="secondary" onClick={() => setViewMode('installed')}>
              <Package className="w-4 h-4" />
              My Modules ({installedIds.size})
            </Button>
          ) : (
            <Button variant="secondary" onClick={() => setViewMode('browse')}>
              <ShoppingCart className="w-4 h-4" />
              Browse Marketplace
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={loadData} disabled={loading}>
            <Loader2 className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-4">
          <p className="text-sm text-red-400">{error}</p>
          <Button size="sm" variant="ghost" onClick={loadData} className="mt-2">
            Retry
          </Button>
        </div>
      )}

      {/* Search & filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
          <input
            type="text"
            placeholder="Search modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-900 border border-surface-800 rounded-lg pl-10 pr-4 py-2 text-sm text-surface-200 
              placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30"
          />
        </div>
        <div className="flex items-center gap-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                cat === activeCategory
                  ? 'bg-primary-600/10 text-primary-400 border border-primary-600/20'
                  : 'text-surface-500 hover:text-surface-300 hover:bg-surface-800 border border-transparent'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <button className="p-2 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800">
          <Filter className="w-4 h-4" />
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
          <span className="ml-3 text-sm text-surface-500">Loading marketplace...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && displayedModules.length === 0 && (
        <div className="text-center py-20">
          <Package className="w-12 h-12 text-surface-600 mx-auto mb-4" />
          <p className="text-surface-500 text-sm">
            {viewMode === 'installed'
              ? 'No modules installed yet. Browse the marketplace to find modules!'
              : 'No modules match your search.'}
          </p>
        </div>
      )}

      {/* Module grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedModules.map((mod) => {
            const isInstalled = installedIds.has(mod.id)
            const isInstalling = installingId === mod.id

            return (
              <Card key={mod.id} hover className="flex flex-col">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-accent-600/10 flex items-center justify-center">
                    <ShoppingCart className="w-5 h-5 text-accent-400" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-surface-800 text-surface-500 rounded-md text-[10px] font-medium">
                      {mod.category}
                    </span>
                    {isInstalled && (
                      <span className="px-2 py-0.5 bg-green-900/20 text-green-400 rounded-md text-[10px] font-medium border border-green-800/30">
                        Installed
                      </span>
                    )}
                  </div>
                </CardHeader>
                <h3 className="text-sm font-semibold text-surface-200 mb-1">{mod.name}</h3>
                <p className="text-xs text-surface-500 mb-3 flex-1">{mod.description}</p>

                {/* Features preview */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {mod.features.slice(0, 3).map((f) => (
                    <span
                      key={f}
                      className="px-1.5 py-0.5 bg-surface-800/50 text-surface-400 rounded text-[10px]"
                    >
                      {f}
                    </span>
                  ))}
                  {mod.features.length > 3 && (
                    <span className="px-1.5 py-0.5 text-surface-500 rounded text-[10px]">
                      +{mod.features.length - 3}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-warning-400">
                      <Star className="w-3.5 h-3.5 fill-current" />
                      {mod.rating}
                    </span>
                    <span className="flex items-center gap-1 text-surface-500">
                      <Download className="w-3.5 h-3.5" />
                      {mod.downloads}
                    </span>
                    <span className="text-surface-600">v{mod.version}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-surface-200">{mod.price_label}</span>
                    <Button
                      size="sm"
                      variant={isInstalled ? 'secondary' : 'primary'}
                      onClick={() => handleInstallToggle(mod.id, isInstalled)}
                      disabled={isInstalling}
                    >
                      {isInstalling ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : isInstalled ? (
                        <>
                          <Check className="w-3 h-3" />
                          Installed
                        </>
                      ) : (
                        'Install'
                      )}
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Installed count footer */}
      {viewMode === 'browse' && !loading && installedIds.size > 0 && (
        <div className="text-center py-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setViewMode('installed')}
            className="text-surface-500"
          >
            <Package className="w-4 h-4" />
            View {installedIds.size} installed module{installedIds.size !== 1 ? 's' : ''}
          </Button>
        </div>
      )}
    </div>
  )
}