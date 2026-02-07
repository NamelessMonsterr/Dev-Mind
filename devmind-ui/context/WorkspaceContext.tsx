"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
  member_count: number;
}

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  loading: boolean;
  selectWorkspace: (workspaceId: string) => void;
  createWorkspace: (name: string, slug: string, description?: string) => Promise<Workspace>;
  refreshWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { accessToken, user } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  // Load workspaces when user logs in
  useEffect(() => {
    if (user && accessToken) {
      refreshWorkspaces();
    } else {
      setWorkspaces([]);
      setCurrentWorkspace(null);
      setLoading(false);
    }
  }, [user, accessToken]);

  const refreshWorkspaces = async () => {
    if (!accessToken) return;

    try {
      const response = await fetch(`${API_BASE_URL}/workspaces`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data);

        // Select first workspace or previously selected
        const savedWorkspaceId = localStorage.getItem('current_workspace_id');
        const workspace = savedWorkspaceId 
          ? data.find((w: Workspace) => w.id === savedWorkspaceId) 
          : data[0];
        
        if (workspace) {
          setCurrentWorkspace(workspace);
          localStorage.setItem('current_workspace_id', workspace.id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectWorkspace = (workspaceId: string) => {
    const workspace = workspaces.find(w => w.id === workspaceId);
    if (workspace) {
      setCurrentWorkspace(workspace);
      localStorage.setItem('current_workspace_id', workspaceId);
    }
  };

  const createWorkspace = async (name: string, slug: string, description?: string): Promise<Workspace> => {
    if (!accessToken) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(`${API_BASE_URL}/workspaces`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        name,
        slug: slug.toLowerCase(),
        description
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create workspace');
    }

    const workspace = await response.json();
    await refreshWorkspaces();
    return workspace;
  };

  return (
    <WorkspaceContext.Provider value={{
      workspaces,
      currentWorkspace,
      loading,
      selectWorkspace,
      createWorkspace,
      refreshWorkspaces
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
