import { useState } from "react";
import { Link } from "react-router-dom";
import { PlanIcon } from "../components/ui";
import {
  PageHeader,
  PageContainer,
  Badge,
  Button,
  ListCard,
  ListItem,
  PlayIcon,
  StopIcon,
  ChevronRightIcon,
  TrashIcon,
} from "../components/ui";
import { usePlans, useActivatePlan, useDeactivatePlan, useDeletePlan } from "../lib/queries";
import CreatePlanModal from "../components/CreatePlanModal";
import Modal from "../components/Modal";

export default function PlansList() {
  const { data: plans = [] } = usePlans();
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const activatePlan = useActivatePlan();
  const deactivatePlan = useDeactivatePlan();
  const deletePlan = useDeletePlan();

  return (
    <PageContainer>
      <PageHeader
        title="Plans"
        icon={<PlanIcon className="h-5 w-5" />}
        description="Create and manage Kanban plans. Assign agents to collaborate in the background."
        action={
          <Button onClick={() => setModalOpen(true)}>
            <PlanIcon className="mr-1.5 h-4 w-4" />
            Add Plan
          </Button>
        }
      />

      <ListCard emptyMessage='No plans yet. Click "Add Plan" to create one.'>
        {plans.map((plan) => {
          const isActive = plan.status === "active";
          return (
            <ListItem key={plan.id}>
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-claude-accent/10 text-claude-accent">
                <PlanIcon className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <Link
                    to={`/plans/${plan.id}`}
                    className="text-sm font-medium text-claude-text-primary hover:text-claude-accent transition-colors truncate"
                  >
                    {plan.name}
                  </Link>
                  <Badge status={plan.status} />
                </div>
                {plan.description ? (
                  <p className="mt-0.5 line-clamp-2 text-xs text-claude-text-muted">{plan.description}</p>
                ) : null}
              </div>
              <div className="flex items-center gap-1.5">
                {isActive ? (
                  <button
                    onClick={() => deactivatePlan.mutate(plan.id)}
                    disabled={deactivatePlan.isPending}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-red-600 bg-red-50 ring-1 ring-red-600/20 hover:bg-red-100 transition-colors disabled:opacity-50"
                  >
                    <StopIcon className="h-2.5 w-2.5" />
                    Pause
                  </button>
                ) : (
                  <button
                    onClick={() => activatePlan.mutate(plan.id)}
                    disabled={activatePlan.isPending}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-green-700 bg-green-50 ring-1 ring-green-600/20 hover:bg-green-100 transition-colors disabled:opacity-50"
                  >
                    <PlayIcon className="h-2.5 w-2.5" />
                    Activate
                  </button>
                )}
                <button
                  onClick={() => setDeleteTarget({ id: plan.id, name: plan.name })}
                  className="rounded p-1 text-claude-border-strong hover:text-red-500 hover:bg-red-50 transition-all"
                  title="Delete plan"
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                </button>
                <Link
                  to={`/plans/${plan.id}`}
                  className="rounded p-1 text-claude-border-strong hover:text-claude-accent hover:bg-claude-surface transition-all"
                >
                  <ChevronRightIcon className="h-3.5 w-3.5" />
                </Link>
              </div>
            </ListItem>
          );
        })}
      </ListCard>

      <CreatePlanModal open={modalOpen} onClose={() => setModalOpen(false)} />

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Plan" size="default">
        <p className="mb-4 text-sm text-claude-text-secondary">
          Are you sure you want to delete <strong>{deleteTarget?.name}</strong>? This will permanently remove the plan
          and all its tasks, artifacts, and comments. This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              if (deleteTarget) {
                deletePlan.mutate(deleteTarget.id, {
                  onSuccess: () => setDeleteTarget(null),
                });
              }
            }}
            disabled={deletePlan.isPending}
          >
            {deletePlan.isPending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </Modal>
    </PageContainer>
  );
}
