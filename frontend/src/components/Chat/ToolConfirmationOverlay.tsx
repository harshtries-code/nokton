import React from 'react';
import { useConversationStore } from '../../stores/conversationStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ConfirmDialog } from '../Common/ConfirmDialog';

export function ToolConfirmationOverlay() {
  const pendingToolCalls = useConversationStore((s) => s.pendingToolCalls);
  const { confirmTool } = useWebSocket();

  const currentConfirm = pendingToolCalls.find((tc) => tc.requires_confirm);

  if (!currentConfirm) return null;

  const handleConfirm = (approved: boolean) => {
    confirmTool(currentConfirm.id, approved, currentConfirm.name, currentConfirm.args);
  };

  return (
    <ConfirmDialog
      title="Confirm Tool Call"
      message={`${currentConfirm.name} wants to run with args: ${JSON.stringify(currentConfirm.args, null, 2)}`}
      onConfirm={() => handleConfirm(true)}
      onCancel={() => handleConfirm(false)}
    />
  );
}