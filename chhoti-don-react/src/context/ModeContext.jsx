import React, { createContext, useContext, useState, useMemo, useCallback, useEffect } from 'react';

const MODE_STORAGE_KEY = 'chhoti-don:mode:v1';

const ModeContext = createContext({
  mode: 'chat',
  setMode: () => {},
  isCodeMode: false,
  isChatMode: true,
});

// eslint-disable-next-line react-refresh/only-export-components
export const useMode = () => useContext(ModeContext);

export function ModeProvider({ children, initialMode = 'chat' }) {
  const [mode, setModeState] = useState(() => {
    try {
      const saved = localStorage.getItem(MODE_STORAGE_KEY);
      if (saved === 'chat' || saved === 'code') return saved;
    } catch {
      /* ignore storage error */
    }
    return initialMode;
  });

  const setMode = useCallback((newMode) => {
    const validMode = newMode === 'code' ? 'code' : 'chat';
    setModeState(validMode);
    try {
      localStorage.setItem(MODE_STORAGE_KEY, validMode);
    } catch {
      /* ignore storage error */
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(MODE_STORAGE_KEY, mode);
    } catch {
      /* ignore storage error */
    }
  }, [mode]);

  const value = useMemo(
    () => ({
      mode,
      setMode,
      isCodeMode: mode === 'code',
      isChatMode: mode === 'chat',
    }),
    [mode, setMode],
  );

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export default ModeContext;
