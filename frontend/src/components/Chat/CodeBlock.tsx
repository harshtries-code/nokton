import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

export function CodeBlock({ language, code }: { language?: string; code: string }) {
  return (
    <div style={styles.container}>
      {language && <div style={styles.header}>{language}</div>}
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{ margin: 0, borderRadius: 8, fontSize: 12 }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { margin: '8px 0', borderRadius: 8, overflow: 'hidden' },
  header: {
    backgroundColor: '#1f2937',
    color: '#9ca3af',
    padding: '4px 12px',
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase',
  },
};
