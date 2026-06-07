import React, { useState, useRef, useEffect } from 'react';
import { useConversationStore } from '../../stores/conversationStore';

export function InputBar({ onSend, onCancel }: { onSend: (text: string, images?: string[]) => void; onCancel: () => void }) {
  const [text, setText] = useState('');
  const [images, setImages] = useState<string[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const isStreaming = useConversationStore((s) => s.isStreaming);

  useEffect(() => {
    if (!isStreaming && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isStreaming]);

  const readFileAsBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        const comma = result.indexOf(",");
        resolve(comma >= 0 ? result.slice(comma + 1) : result);
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });

  const addFiles = async (files: FileList | File[]) => {
    const out: string[] = [];
    for (const f of Array.from(files)) {
      if (!f.type.startsWith("image/")) continue;
      try {
        out.push(await readFileAsBase64(f));
      } catch {}
    }
    if (out.length) setImages((prev) => [...prev, ...out]);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) await addFiles(e.target.files);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files: File[] = [];
    for (const item of Array.from(items)) {
      if (item.kind === "file") {
        const f = item.getAsFile();
        if (f && f.type.startsWith("image/")) files.push(f);
      }
    }
    if (files.length) {
      e.preventDefault();
      await addFiles(files);
    }
  };

  const removeImage = (idx: number) => {
    setImages((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if ((!trimmed && images.length === 0) || isStreaming) return;
    onSend(trimmed, images);
    setText("");
    setImages([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={styles.container}>
      {images.length > 0 && (
        <div style={styles.thumbs}>
          {images.map((img, idx) => (
            <div key={idx} style={styles.thumb}>
              <img src={`data:image/jpeg;base64,${img}`} style={styles.thumbImg} alt="" />
              <button
                style={styles.thumbRemove}
                onClick={() => removeImage(idx)}
                title="Remove"
                type="button"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      <div style={styles.bar}>
        <button
          style={styles.attachBtn}
          onClick={() => fileRef.current?.click()}
          disabled={isStreaming}
          type="button"
          title="Attach image"
        >
          +
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="Type a message or paste an image..."
          style={styles.input}
          rows={1}
        />
        {isStreaming ? (
          <button style={styles.stopBtn} onClick={onCancel} type="button">
            ■
          </button>
        ) : (
          <button
            style={styles.sendBtn}
            onClick={handleSubmit}
            disabled={!text.trim() && images.length === 0}
            type="button"
          >
            ▶
          </button>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "12px 20px",
    borderTop: "1px solid #1f2937",
    backgroundColor: "#0f0f23",
  },
  bar: {
    display: "flex",
    alignItems: "flex-end",
    gap: 8,
    backgroundColor: "#1a1a2e",
    borderRadius: 12,
    padding: "8px 12px",
    border: "1px solid #2a2a4a",
  },
  input: {
    flex: 1,
    backgroundColor: "transparent",
    color: "#e0e0e0",
    border: "none",
    outline: "none",
    fontSize: 14,
    resize: "none",
    fontFamily: "inherit",
    maxHeight: 120,
  },
  sendBtn: {
    backgroundColor: "#7c3aed",
    color: "#fff",
    border: "none",
    width: 36,
    height: 36,
    borderRadius: "50%",
    cursor: "pointer",
    fontSize: 16,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  stopBtn: {
    backgroundColor: "#ef4444",
    color: "#fff",
    border: "none",
    width: 36,
    height: 36,
    borderRadius: "50%",
    cursor: "pointer",
    fontSize: 16,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  attachBtn: {
    backgroundColor: "transparent",
    color: "#9ca3af",
    border: "1px solid #2a2a4a",
    width: 32,
    height: 32,
    borderRadius: "50%",
    cursor: "pointer",
    fontSize: 20,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    padding: 0,
    lineHeight: 1,
  },
  thumbs: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 8,
  },
  thumb: {
    position: "relative",
    width: 60,
    height: 60,
    borderRadius: 6,
    overflow: "hidden",
    border: "1px solid #2a2a4a",
  },
  thumbImg: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  thumbRemove: {
    position: "absolute",
    top: 2,
    right: 2,
    width: 18,
    height: 18,
    borderRadius: "50%",
    border: "none",
    backgroundColor: "rgba(0,0,0,0.6)",
    color: "#fff",
    cursor: "pointer",
    fontSize: 12,
    lineHeight: 1,
    padding: 0,
  },
};
