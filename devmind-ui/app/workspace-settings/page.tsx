"use client";

import { useState, useEffect } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Settings, Users, Trash2, Save } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function WorkspaceSettingsPage() {
  const { currentWorkspace, refreshWorkspaces } = useWorkspace();
  const { accessToken } = useAuth();
  
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (currentWorkspace) {
      setName(currentWorkspace.name);
      setDescription(currentWorkspace.description || '');
      loadMembers();
    }
  }, [currentWorkspace]);

  const loadMembers = async () => {
    if (!currentWorkspace || !accessToken) return;

    try {
      const response = await fetch(`${API_BASE_URL}/workspaces/${currentWorkspace.id}`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setMembers(data.members || []);
      }
    } catch (err) {
      console.error('Failed to load members:', err);
    }
  };

  const handleSave = async () => {
    if (!currentWorkspace || !accessToken) return;
    
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/workspaces/${currentWorkspace.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ name, description })
      });

      if (response.ok) {
        setSuccess('Workspace updated successfully');
        await refreshWorkspaces();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to update workspace');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update workspace');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteWorkspace = async () => {
    if (!currentWorkspace || !accessToken) return;
    
    if (!confirm(`Are you sure you want to delete "${currentWorkspace.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/workspaces/${currentWorkspace.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });

      if (response.ok) {
        window.location.href = '/';  // Redirect to home
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to delete workspace');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete workspace');
    }
  };

  if (!currentWorkspace) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">No workspace selected</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-8 h-8 text-primary" />
        <h1 className="text-3xl font-bold">Workspace Settings</h1>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-500/20 border border-green-500/50 rounded-lg text-green-200">
          {success}
        </div>
      )}

      {/* General Settings */}
      <div className="bg-card border border-border rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          General
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Workspace Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="My Workspace"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Slug</label>
            <input
              type="text"
              value={currentWorkspace.slug}
              disabled
              className="w-full px-4 py-2 bg-muted border border-border rounded-md text-muted-foreground cursor-not-allowed"
            />
            <p className="text-xs text-muted-foreground mt-1">Slug cannot be changed</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              rows={4}
              placeholder="Describe your workspace..."
            />
          </div>

          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2 bg-primary hover:bg-primary/80 rounded-md transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Members */}
      <div className="bg-card border border-border rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5" />
          Members ({members.length})
        </h2>

        <div className="space-y-3">
          {members.map((member) => (
            <div key={member.id} className="flex items-center justify-between p-3 bg-accent/30 rounded-md">
              <div>
                <p className="font-medium">{member.username}</p>
                <p className="text-sm text-muted-foreground">{member.email}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 bg-primary/20 text-primary text-sm rounded-full">
                  {member.role}
                </span>
                {member.role !== 'owner' && (
                  <button
                    className="text-red-400 hover:text-red-300"
                    title="Remove member"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-card border border-red-500/50 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 text-red-400">Danger Zone</h2>
        
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Delete Workspace</p>
            <p className="text-sm text-muted-foreground">Permanently delete this workspace and all its data</p>
          </div>
          <button
            onClick={handleDeleteWorkspace}
            className="flex items-center gap-2 px-6 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 rounded-md transition-colors text-red-300"
          >
            <Trash2 className="w-4 h-4" />
            Delete Workspace
          </button>
        </div>
      </div>
    </div>
  );
}
