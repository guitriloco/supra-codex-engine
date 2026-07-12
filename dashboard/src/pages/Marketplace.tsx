import { Card, CardHeader } from '@/components/Card'
import { Button } from '@/components/Button'
import { ShoppingCart, Star, Download, Search, Filter } from 'lucide-react'

const modules = [
  {
    name: 'E-commerce Price Tracker',
    description: 'Monitor competitor pricing across major retailers. Supports Amazon, Walmart, and more.',
    author: 'Supra-Codex',
    rating: 4.8,
    downloads: 1240,
    price: 'Free',
    category: 'Scraping',
  },
  {
    name: 'LinkedIn Lead Generator',
    description: 'Extract and enrich LinkedIn profiles for B2B lead generation pipelines.',
    author: 'DataFlow Labs',
    rating: 4.6,
    downloads: 873,
    price: '$29',
    category: 'Leads',
  },
  {
    name: 'News Aggregator Pro',
    description: 'Real-time news aggregation with sentiment analysis and topic clustering.',
    author: 'IntelStack',
    rating: 4.5,
    downloads: 654,
    price: '$19',
    category: 'Analysis',
  },
  {
    name: 'Social Sentiment Analyzer',
    description: 'Analyze social media sentiment for brands, products, or trends.',
    author: 'TrendViz',
    rating: 4.3,
    downloads: 421,
    price: '$39',
    category: 'Analysis',
  },
  {
    name: 'Job Board Scanner',
    description: 'Scrape job postings from major platforms for market research and hiring insights.',
    author: 'RecruitIntel',
    rating: 4.7,
    downloads: 312,
    price: 'Free',
    category: 'Scraping',
  },
  {
    name: 'SEO Rank Tracker',
    description: 'Track search engine rankings for keywords across Google, Bing, and DuckDuckGo.',
    author: 'RankWatch',
    rating: 4.4,
    downloads: 567,
    price: '$15',
    category: 'SEO',
  },
]

const categories = ['All', 'Scraping', 'Leads', 'Analysis', 'SEO', 'Enrichment']

export default function Marketplace() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Nectar Marketplace</h1>
          <p className="text-sm text-surface-500 mt-1">Discover and install automation modules</p>
        </div>
        <Button variant="secondary">
          <ShoppingCart className="w-4 h-4" />
          My Purchases
        </Button>
      </div>

      {/* Search & filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
          <input
            type="text"
            placeholder="Search modules..."
            className="w-full bg-surface-900 border border-surface-800 rounded-lg pl-10 pr-4 py-2 text-sm text-surface-200 
              placeholder-surface-600 focus:outline-none focus:border-primary-600/50 focus:ring-1 focus:ring-primary-600/30"
          />
        </div>
        <div className="flex items-center gap-1">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                cat === 'All'
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

      {/* Module grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((mod) => (
          <Card key={mod.name} hover className="flex flex-col">
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-accent-600/10 flex items-center justify-center">
                <ShoppingCart className="w-5 h-5 text-accent-400" />
              </div>
              <span className="px-2 py-0.5 bg-surface-800 text-surface-500 rounded-md text-[10px] font-medium">
                {mod.category}
              </span>
            </CardHeader>
            <h3 className="text-sm font-semibold text-surface-200 mb-1">{mod.name}</h3>
            <p className="text-xs text-surface-500 mb-4 flex-1">{mod.description}</p>
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
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-surface-200">{mod.price}</span>
                <Button size="sm">Install</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}