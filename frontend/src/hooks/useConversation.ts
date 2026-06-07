import { useCallback, useEffect } from 'react';
import { getWebSocket } from './useWebSocket';
import { useConversationStore } from '../stores/conversationStore';

export function useConversation() {
  const store = useConversationStore();

  const newConversation = useCallback(() => {
    store.clearMessages();
    getWebSocket().newConversation();
  }, [store]);

  const listConversations = useCallback(() => {
    getWebSocket().listConversations();
  }, []);

  const loadConversation = useCallback((id: string) => {
    getWebSocket().loadConversation(id);
  }, []);

  useEffect(() => {
    listConversations();
  }, [listConversations]);

  return { newConversation, listConversations, loadConversation };
}
