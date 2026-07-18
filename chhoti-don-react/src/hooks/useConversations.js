import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const STORAGE_KEY = 'chhoti-don:conversations:v1';
const ACTIVE_KEY = 'chhoti-don:activeConversation:v1';
const DEFAULT_TITLE = 'New conversation';

const uid = () => `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

function makeConversation() {
  const now = Date.now();
  return { id: uid(), title: DEFAULT_TITLE, messages: [], createdAt: now, updatedAt: now };
}

function deriveTitle(text) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return DEFAULT_TITLE;
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean;
}

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed) && parsed.length) {
      const activeId = localStorage.getItem(ACTIVE_KEY);
      const active = parsed.some((c) => c.id === activeId) ? activeId : parsed[0].id;
      return { conversations: parsed, activeId: active };
    }
  } catch {
    /* corrupt storage → start fresh */
  }
  const fresh = makeConversation();
  return { conversations: [fresh], activeId: fresh.id };
}

/**
 * Local, persisted conversation store.
 * - Conversations and the active id survive refresh via localStorage.
 * - `private mode` (paused) keeps everything in memory but stops writing to disk.
 */
export default function useConversations() {
  const initial = useMemo(loadInitial, []);
  const [conversations, setConversations] = useState(initial.conversations);
  const [activeId, setActiveId] = useState(initial.activeId);
  const [paused, setPaused] = useState(false);
  const privateSnapshotRef = useRef(null);

  const activeIdRef = useRef(activeId);
  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  // Persist (unless private mode is on).
  useEffect(() => {
    if (paused) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
      localStorage.setItem(ACTIVE_KEY, activeId);
    } catch {
      /* storage full / unavailable → ignore, stay in-memory */
    }
  }, [conversations, activeId, paused]);

  const updateActiveMessages = useCallback((updater) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== activeIdRef.current) return c;
        const messages = typeof updater === 'function' ? updater(c.messages) : updater;
        let title = c.title;
        if (title === DEFAULT_TITLE || !title) {
          const firstUser = messages.find((m) => m.role === 'user');
          if (firstUser) title = deriveTitle(firstUser.text);
        }
        return { ...c, messages, title, updatedAt: Date.now() };
      }),
    );
  }, []);

  const createConversation = useCallback(() => {
    const fresh = makeConversation();
    setConversations((prev) => {
      // Drop other empty, unused conversations to avoid clutter.
      const pruned = prev.filter((c) => c.messages.length > 0);
      return [fresh, ...pruned];
    });
    setActiveId(fresh.id);
    return fresh.id;
  }, []);

  const selectConversation = useCallback((id) => {
    setActiveId((current) => (current === id ? current : id));
  }, []);

  const clearAllConversations = useCallback(() => {
    const fresh = makeConversation();
    setConversations([fresh]);
    setActiveId(fresh.id);
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(ACTIVE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const setPrivateMode = useCallback((on) => {
    const enabled = Boolean(on);
    if (enabled) {
      setConversations((current) => {
        privateSnapshotRef.current = { conversations: current, activeId: activeIdRef.current };
        return current;
      });
      setPaused(true);
      return;
    }

    const snapshot = privateSnapshotRef.current;
    if (snapshot) {
      setConversations(snapshot.conversations);
      setActiveId(snapshot.activeId);
      privateSnapshotRef.current = null;
    }
    setPaused(false);
  }, []);

  const sorted = useMemo(
    () => [...conversations].sort((a, b) => b.updatedAt - a.updatedAt),
    [conversations],
  );

  const activeConversation =
    conversations.find((c) => c.id === activeId) || conversations[0] || makeConversation();

  return {
    conversations: sorted,
    activeConversation,
    activeId,
    privateMode: paused,
    setPrivateMode,
    createConversation,
    selectConversation,
    updateActiveMessages,
    clearAllConversations,
  };
}
