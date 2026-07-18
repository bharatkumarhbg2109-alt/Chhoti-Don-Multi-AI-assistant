import { useCallback, useEffect, useRef, useState } from 'react';
import {
  listConversations as apiList,
  createConversation as apiCreate,
  getConversation as apiGet,
  patchConversation as apiPatch,
  deleteConversation as apiDelete,
  importConversations as apiImport,
} from '../services/chatApi';

const LEGACY_KEY = 'chhoti-don:conversations:v1';
const MIGRATED_KEY = 'chhoti-don:migrated:v2';

let seq = 0;
const localId = () => `local_${Date.now().toString(36)}_${(seq += 1)}`;

function fmtTime(created) {
  if (!created) return 'Now';
  try {
    return new Date(created * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Now';
  }
}

/** Map a backend message record to the frontend chat-message shape. */
function toClientMessage(m) {
  return {
    id: m.id,
    role: m.role,
    text: m.content,
    timestamp: fmtTime(m.created_at),
    isError: m.status === 'error',
    meta: {
      model: m.model,
      provider: m.provider,
      ...(m.metadata || {}),
    },
  };
}

/** Normalise a backend conversation summary for the sidebar. */
function toClientConversation(c) {
  return {
    ...c,
    updatedAt: (c.updated_at || 0) * 1000,
    messageCount: c.message_count || 0,
  };
}

/**
 * Backend-backed conversation store.
 *
 * - The list, titles and messages live in the Flask/SQLite backend and survive
 *   restart. Conversations are created lazily (on the first sent message) so the
 *   sidebar never fills with empty drafts.
 * - Private mode keeps the active draft entirely in volatile memory (nothing is
 *   written to the backend).
 * - A one-time migration imports any legacy localStorage history.
 */
export default function useConversations() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null); // null = unsaved draft
  const [activeMessages, setActiveMessagesState] = useState([]);
  const [privateMode, setPrivateModeState] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [listError, setListError] = useState(null);
  const [migrationInfo, setMigrationInfo] = useState(null);

  const activeIdRef = useRef(activeId);
  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  const refresh = useCallback(async (query) => {
    setLoadingList(true);
    try {
      const data = await apiList(query);
      const convs = (data?.conversations || []).map(toClientConversation);
      setConversations(convs);
      setListError(null);
      return convs;
    } catch (err) {
      if (err?.name === 'AbortError') return [];
      setListError(err?.message || 'Failed to load conversations.');
      return [];
    } finally {
      setLoadingList(false);
    }
  }, []);

  // One-time legacy migration, then initial load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const alreadyMigrated = localStorage.getItem(MIGRATED_KEY) === '1';
        const raw = localStorage.getItem(LEGACY_KEY);
        if (!alreadyMigrated && raw) {
          const parsed = JSON.parse(raw);
          const withMsgs = Array.isArray(parsed)
            ? parsed.filter((c) => c && Array.isArray(c.messages) && c.messages.length)
            : [];
          if (withMsgs.length) {
            const res = await apiImport(withMsgs);
            if (!cancelled) setMigrationInfo(res);
          }
          localStorage.setItem(MIGRATED_KEY, '1');
        }
      } catch {
        /* migration is best-effort; never blocks the app */
      }
      if (!cancelled) await refresh();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const setActiveMessages = useCallback((updater) => {
    setActiveMessagesState((prev) => (typeof updater === 'function' ? updater(prev) : updater));
  }, []);

  const selectConversation = useCallback(async (id) => {
    if (!id) return;
    setActiveId(id);
    setLoadingMessages(true);
    try {
      const data = await apiGet(id);
      const msgs = (data?.conversation?.messages || []).map(toClientMessage);
      // Guard against a race if the user switched again mid-fetch.
      if (activeIdRef.current === id) setActiveMessagesState(msgs);
    } catch {
      if (activeIdRef.current === id) setActiveMessagesState([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  const newDraft = useCallback(() => {
    setActiveId(null);
    setActiveMessagesState([]);
  }, []);

  /**
   * Ensure a backend conversation exists for the active turn.
   * Returns the conversation id, or null when in private mode (volatile).
   */
  const ensureConversationId = useCallback(async () => {
    if (privateMode) return null;
    if (activeIdRef.current) return activeIdRef.current;
    const data = await apiCreate();
    const conv = toClientConversation(data.conversation);
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    return conv.id;
  }, [privateMode]);

  const onTurnPersisted = useCallback(() => {
    // Refresh summaries so titles/order/counts reflect the saved turn.
    refresh();
  }, [refresh]);

  const renameConversation = useCallback(async (id, title) => {
    const data = await apiPatch(id, { title });
    const conv = toClientConversation(data.conversation);
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, ...conv } : c)));
    return conv;
  }, []);

  const removeConversation = useCallback(
    async (id) => {
      await apiDelete(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeIdRef.current === id) newDraft();
    },
    [newDraft],
  );

  const setPrivateMode = useCallback(
    (on) => {
      const enabled = Boolean(on);
      setPrivateModeState(enabled);
      // Entering private mode starts a clean volatile draft.
      if (enabled) newDraft();
    },
    [newDraft],
  );

  return {
    conversations,
    activeId,
    activeMessages,
    privateMode,
    loadingList,
    loadingMessages,
    listError,
    migrationInfo,
    setActiveMessages,
    setPrivateMode,
    refresh,
    selectConversation,
    newDraft,
    ensureConversationId,
    onTurnPersisted,
    renameConversation,
    removeConversation,
  };
}
