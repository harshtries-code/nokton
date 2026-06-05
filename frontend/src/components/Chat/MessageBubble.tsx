import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types/messages';
import { ToolCallCard } from './ToolCallCard';
import { ReasoningBlock } from './ReasoningBlock';

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div style={styles.wrapper(isUser)}>
      <div style={styles.avatar(isUser)}>
        {isUser ? 'U' : 'N'}
      </div>
      <div style={styles.bubble(isUser)}>
        {message.reasoning && (
          <ReasoningBlock text={message.reasoning} />
        )}
        <div style={styles.content}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div style={styles.tools}>
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, any> = {
  wrapper: (isUser: boolean) => ({
    display: 'flex',
    flexDirection: isUser ? 'row-reverse' : 'row',
    alignItems: 'flex-start',
    gap: 10,
  }),
  avatar: (isUser: boolean) => ({
    width: 32,
    height: 32,
    borderRadius: '50%',
    backgroundColor: isUser ? '#7c3aed' : '#1e40af',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 13,
    fontWeight: 700,
    flexShrink: 0,
  }),
  bubble: (isUser: boolean) => ({
    maxWidth: '75%',
    backgroundColor: isUser ? '#1e1b4b' : '#1a1a2e',
    color: '#e0e0e0',
    padding: '10px 14px',
    borderRadius: 12,
    borderBottomRightRadius: isUser ? 4 : 12,
    borderBottomLeftRadius: isUser ? 12 : 4,
    fontSize: 14,
    lineHeight: 1.5,
  }),
  content: { wordBreak: 'break-word' },
  tools: { marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 },
};
