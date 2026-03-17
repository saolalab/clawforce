import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api";
import { queryKeys } from "../../../lib/queries";
import type { WorkspaceFiles } from "../../../lib/types";

interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}

/**
 * Hook for managing agent workspace files and directories.
 * Provides CRUD operations for the workspace file browser.
 */
export function useWorkspace(agentId: string | undefined) {
  const queryClient = useQueryClient();

  const filesQuery = useQuery({
    queryKey: queryKeys.workspaceFiles(agentId!),
    queryFn: () => api.agents.workspaceFiles(agentId!),
    enabled: !!agentId,
    staleTime: 10_000,
    refetchInterval: 15_000,
  });

  const fileQuery = (path: string) =>
    useQuery({
      queryKey: queryKeys.workspaceFile(agentId!, path),
      queryFn: () => api.agents.workspaceFile(agentId!, path),
      enabled: !!agentId && !!path,
      staleTime: 5_000,
      refetchInterval: 10_000,
    });

  const saveFileMutation = useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) =>
      api.agents.saveWorkspaceFile(agentId!, path, content),
    onSuccess: (_, { path }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaceFile(agentId!, path),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaceFiles(agentId!),
      });
    },
  });

  const deleteFileMutation = useMutation({
    mutationFn: (path: string) => api.agents.deleteWorkspaceFile(agentId!, path),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaceFiles(agentId!),
      });
    },
  });

  const renameFileMutation = useMutation({
    mutationFn: ({ oldPath, newPath }: { oldPath: string; newPath: string }) =>
      api.agents.renameWorkspaceFile(agentId!, oldPath, newPath),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaceFiles(agentId!),
      });
    },
  });

  const moveFileMutation = useMutation({
    mutationFn: ({ source, target }: { source: string; target: string }) =>
      api.agents.moveWorkspaceFile(agentId!, source, target),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspaceFiles(agentId!),
      });
    },
  });

  // Build tree structure from flat file list
  const buildFileTree = (files: string[]): FileNode[] => {
    const root: FileNode[] = [];
    const map = new Map<string, FileNode>();

    files.sort().forEach((path) => {
      const parts = path.split("/").filter(Boolean);
      let currentPath = "";

      parts.forEach((part, index) => {
        const isLast = index === parts.length - 1;
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;

        if (!map.has(currentPath)) {
          const node: FileNode = {
            name: part,
            path: currentPath,
            type: isLast && !path.endsWith("/") ? "file" : "directory",
            children: isLast ? undefined : [],
          };
          map.set(currentPath, node);

          if (parentPath) {
            const parent = map.get(parentPath);
            if (parent && parent.children) {
              parent.children.push(node);
            }
          } else {
            root.push(node);
          }
        }
      });
    });

    return root;
  };

  return {
    files: (filesQuery.data as WorkspaceFiles | undefined)?.files || [],
    fileTree: buildFileTree((filesQuery.data as WorkspaceFiles | undefined)?.files || []),
    isLoading: filesQuery.isLoading,
    isError: filesQuery.isError,
    refetch: filesQuery.refetch,
    getFile: fileQuery,
    saveFile: saveFileMutation.mutate,
    deleteFile: deleteFileMutation.mutate,
    renameFile: renameFileMutation.mutate,
    moveFile: moveFileMutation.mutate,
    isSaving: saveFileMutation.isPending,
    isDeleting: deleteFileMutation.isPending,
  };
}
