import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { ToolConfirmationOverlay } from './ToolConfirmationOverlay';
import { useConversationStore } from '../../stores/conversationStore';

export function MessageList() {
  const messages = useConversationStore((s) => s.messages);
  const isStreaming = useConversationStore((s) => s.isStreaming);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return (
      <div style={styles.empty}>
        <h2 style={styles.emptyTitle}>Nokton</h2>
        <p style={styles.emptyText}>Your desktop AI assistant. Ask me anything!</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <ToolConfirmationOverlay />
      <div ref={bottomRef} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6b7280',
  },
  emptyTitle: { fontSize: 28, fontWeight: 700, color: '#7c3aed', margin: 0 },
  emptyText: { fontSize: 14, marginTop: 8 },
};
