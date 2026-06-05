import React, { useState, useRef, useEffect } from 'react';
import { useConversationStore } from '../../stores/conversationStore';

export function InputBar({ onSend, onCancel }: { onSend: (text: string) => void; onCancel: () => void }) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isStreaming = useConversationStore((s) => s.isStreaming);

  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.bar}>
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          style={styles.input}
          rows={1}
        />
        {isStreaming ? (
          <button style={styles.stopBtn} onClick={onCancel}>
            ■
          </button>
        ) : (
          <button style={styles.sendBtn} onClick={handleSubmit} disabled={!text.trim()}>
            ▶
          </button>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '12px 20px',
    borderTop: '1px solid #1f2937',
    backgroundColor: '#0f0f23',
  },
  bar: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 8,
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    padding: '8px 12px',
    border: '1px solid #2a2a4a',
  },
  input: {
    flex: 1,
    backgroundColor: 'transparent',
    color: '#e0e0e0',
    border: 'none',
    outline: 'none',
    fontSize: 14,
    resize: 'none',
    fontFamily: 'inherit',
    maxHeight: 120,
  },
  sendBtn: {
    backgroundColor: '#7c3aed',
    color: '#fff',
    border: 'none',
    width: 36,
    height: 36,
    borderRadius: '50%',
    cursor: 'pointer',
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  stopBtn: {
    backgroundColor: '#ef4444',
    color: '#fff',
    border: 'none',
    width: 36,
    height: 36,
    borderRadius: '50%',
    cursor: 'pointer',
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
};
