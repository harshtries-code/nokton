import { useCallback } from 'react';
import { getWebSocket } from './useWebSocket';
import { useConversationStore } from '../stores/conversationStore';

export function useConversation() {
  const store = useConversationStore();

  const newConversation = useCallback(() => {
    store.clearMessages();
    getWebSocket().newConversation();
  }, []);

  const listConversations = useCallback(() => {
    getWebSocket().listConversations();
  }, []);

  return { newConversation, listConversations };
}
