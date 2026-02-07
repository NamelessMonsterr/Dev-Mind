"use client";

import { useState } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { Check, ChevronsUpDown, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function WorkspaceSwitcher() {
  const { workspaces, currentWorkspace, selectWorkspace, loading } = useWorkspace();
  const [isOpen, setIsOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  if (loading || !currentWorkspace) {
    return (
      <div className="p-3 bg-accent/50 rounded-md">
        <div className="h-5 bg-muted animate-pulse rounded"></div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-accent/50 hover:bg-accent rounded-md transition-colors"
      >
        <div className="flex-1 text-left">
          <p className="text-sm font-medium truncate">{currentWorkspace.name}</p>
          <p className="text-xs text-muted-foreground truncate">{currentWorkspace.slug}</p>
        </div>
        <ChevronsUpDown className="w-4 h-4 text-muted-foreground ml-2" />
      </button>

      {isOpen && (
        <div className="bg-card border border-border rounded-md py-1 shadow-lg">
          {workspaces.map((workspace) => (
            <button
              key={workspace.id}
              onClick={() => {
                selectWorkspace(workspace.id);
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-between px-3 py-2 hover:bg-accent transition-colors text-left"
            >
              <div className="flex-1">
                <p className="text-sm font-medium truncate">{workspace.name}</p>
                <p className="text-xs text-muted-foreground truncate">{workspace.slug}</p>
              </div>
              {currentWorkspace.id === workspace.id && (
                <Check className="w-4 h-4 text-primary" />
              )}
            </button>
          ))}
          
          <div className="border-t border-border mt-1 pt-1">
            <button
              onClick={() => {
                setShowCreate(true);
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-accent transition-colors text-primary"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm">Create Workspace</span>
            </button>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateWorkspaceModal onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}

function CreateWorkspaceModal({ onClose }: { onClose: () => void }) {
  const { createWorkspace } = useWorkspace();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await createWorkspace(name, slug, description);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create workspace');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-4">Create Workspace</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded text-red-200 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="My Project"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Slug *</label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
              placeholder="my-project"
              pattern="[a-z0-9-]+"
              required
            />
            <p className="text-xs text-muted-foreground mt-1">Lowercase letters, numbers, and hyphens only</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              rows={3}
              placeholder="Optional description"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              onClick={onClose}
              className="flex-1 bg-accent hover:bg-accent/80"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading}
              className="flex-1 bg-primary hover:bg-primary/80"
            >
              {loading ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
