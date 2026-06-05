import React, { useEffect, useState } from 'react';

export function StreamingText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    setDisplayed(text);
  }, [text]);

  return <span>{displayed}</span>;
}
