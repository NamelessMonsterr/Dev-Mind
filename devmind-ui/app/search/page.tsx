'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { SearchResultCard } from '@/components/SearchResultCard'
import { api, type SearchResult as APISearchResult } from '@/lib/api'
import { Search, Loader2 } from 'lucide-react'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<APISearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsSearching(true)
    try {
      const response = await api.search({
        query,
        top_k: 20,
        use_keyword_search: true
      })
      
      setResults(response.results)
      setSearchTime(response.search_time_ms)
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h1 className="text-2xl font-bold">Semantic Search</h1>
        <p className="text-sm text-muted-foreground">
          Search across your entire codebase
        </p>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-border">
        <form onSubmit={handleSearch} className="flex gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for code, functions, classes..."
            className="flex-1"
            disabled={isSearching}
          />
          <Button type="submit" disabled={isSearching || !query.trim()}>
            {isSearching ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4 mr-2" />
            )}
            Search
          </Button>
        </form>

        {searchTime !== null && (
          <p className="text-xs text-muted-foreground mt-2">
            Found {results.length} results in {searchTime.toFixed(2)}ms
          </p>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {results.length === 0 && !isSearching && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
              <Search className="w-12 h-12 mx-auto text-muted-foreground" />
              <p className="text-muted-foreground">
                {query ? 'No results found' : 'Enter a search query to get started'}
              </p>
            </div>
          </div>
        )}

        {results.map((result, index) => (
          <SearchResultCard key={index} result={result} />
        ))}
      </div>
    </div>
  )
}
