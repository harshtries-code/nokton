import React from 'react';
import { MessageList } from '../Chat/MessageList';
import { InputBar } from '../Chat/InputBar';

export function MainView({ onSendMessage, onCancel }: { onSendMessage: (text: string, images?: string[]) => void; onCancel: () => void }) {
  return (
    <div style={styles.container}>
      <MessageList />
      <InputBar onSend={onSendMessage} onCancel={onCancel} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0f0f23',
    overflow: 'hidden',
  },
};
