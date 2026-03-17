import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api";
import { queryKeys } from "../../../lib/queries";
import type { Agent } from "../../../lib/types";

/**
 * Hook for fetching and managing a single agent's data.
 * Provides agent details with automatic refetching and mutations.
 */
export function useAgent(agentId: string | undefined) {
  const queryClient = useQueryClient();

  const agentQuery = useQuery({
    queryKey: queryKeys.agent(agentId!),
    queryFn: () => api.agents.get(agentId!),
    enabled: !!agentId,
    staleTime: 10_000,
  });

  const startMutation = useMutation({
    mutationFn: () => api.agents.start(agentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agent(agentId!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.claws });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => api.agents.stop(agentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agent(agentId!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.claws });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.agents.delete(agentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.claws });
    },
  });

  return {
    agent: agentQuery.data as Agent | undefined,
    isLoading: agentQuery.isLoading,
    isError: agentQuery.isError,
    error: agentQuery.error,
    refetch: agentQuery.refetch,
    start: startMutation.mutate,
    stop: stopMutation.mutate,
    delete: deleteMutation.mutate,
    isStarting: startMutation.isPending,
    isStopping: stopMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
