'use client'

import { useState} from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Settings as SettingsIcon, Moon, Sun } from 'lucide-react'

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState('http://localhost:8000')
  const [queryExpansion, setQueryExpansion] = useState(true)
  const [defaultProvider, setDefaultProvider] = useState('auto')

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure DevMind preferences
        </p>
      </div>

      {/* Settings */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* API Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">API Configuration</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">API Base URL</label>
              <Input
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* LLM Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">LLM Provider</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Default Provider</label>
              <select
                value={defaultProvider}
                onChange={(e) => setDefaultProvider(e.target.value)}
                className="mt-1 w-full px-3 py-2 rounded-md border border-input bg-background"
              >
                <option value="auto">Auto Select</option>
                <option value="local">Phi-3 (Local)</option>
                <option value="sonnet">Claude Sonnet</option>
                <option value="opus">Claude Opus</option>
              </select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Query Expansion</p>
                <p className="text-xs text-muted-foreground">
                  Expand queries with synonyms
                </p>
              </div>
              <Button
                variant={queryExpansion ? 'default' : 'outline'}
                size="sm"
                onClick={() => setQueryExpansion(!queryExpansion)}
              >
                {queryExpansion ? 'Enabled' : 'Disabled'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Appearance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Theme</p>
                <p className="text-xs text-muted-foreground">
                  Currently in dark mode
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon">
                  <Sun className="w-4 h-4" />
                </Button>
                <Button variant="default" size="icon">
                  <Moon className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">About</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span className="font-mono">0.1.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Phase</span>
              <span>6: Web UI</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Backend</span>
              <span className="font-mono">{apiUrl}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
