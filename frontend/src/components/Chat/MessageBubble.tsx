import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types/messages';
import { ToolCallCard } from './ToolCallCard';
import { ReasoningBlock } from './ReasoningBlock';
import { CodeBlock } from './CodeBlock';

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
          <ReactMarkdown
            components={{
              code({ node, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                const codeStr = String(children).replace(/\n$/, '');
                if (match) {
                  return <CodeBlock language={match[1]} code={codeStr} />;
                }
                return (
                  <code style={styles.inlineCode} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
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
    backgroundColor: isUser ? '#00ff66' : '#0099ff',
    color: isUser ? '#030308' : '#030308',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 13,
    fontWeight: 700,
    flexShrink: 0,
    boxShadow: isUser ? '0 0 8px rgba(0, 255, 102, 0.3)' : '0 0 8px rgba(0, 153, 255, 0.3)',
  }),
  bubble: (isUser: boolean) => ({
    maxWidth: '80%',
    backgroundColor: isUser ? 'rgba(0, 255, 102, 0.08)' : 'rgba(0, 153, 255, 0.06)',
    color: '#e0e0e0',
    padding: '12px 16px',
    borderRadius: 8,
    border: isUser ? '1px solid rgba(0, 255, 102, 0.15)' : '1px solid rgba(0, 153, 255, 0.12)',
    fontSize: 14,
    lineHeight: 1.5,
    fontFamily: '"Share Tech Mono", monospace',
  }),
  content: { wordBreak: 'break-word' as const },
  inlineCode: {
    backgroundColor: 'rgba(0, 255, 102, 0.1)',
    color: '#00ff66',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: '0.85em',
    fontFamily: '"Share Tech Mono", monospace',
  },
  tools: { marginTop: 8, display: 'flex', flexDirection: 'column' as const, gap: 4 },
};
