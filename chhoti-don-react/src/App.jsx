import React, { useCallback, useEffect, useRef, useState } from 'react';
import AmbientBackground from './components/AmbientBackground';
import ChatComposer from './components/ChatComposer';
import ChatMessage from './components/ChatMessage';
import CursorTrail from './components/CursorTrail';
import EmptyState from './components/EmptyState';
import MemoryView from './components/MemoryView';
import SystemStatusView from './components/SystemStatusView';
import CyberView from './components/CyberView';
import HealingView from './components/HealingView';
import SettingsModal from './components/SettingsModal';
import Sidebar from './components/Sidebar';
import ThinkingIndicator from './components/ThinkingIndicator';
import TopBar from './components/TopBar';
import WorkspaceView from './components/WorkspaceView';
import useConversations from './hooks/useConversations';
import { useToast } from './context/ToastContext';
import { getStatus, sendMessage, resetMemory, isDesktop } from './services/chatApi';
import { deriveAiStatus } from './services/status';

const promptIdeas = [
  'Plan my most productive day',
  'Review a technical architecture',
  'Turn notes into a study roadmap',
];

const STREAM_CHUNK = 3;
const STREAM_DELAY = 16;
const MOTION_KEY = 'chhoti-don:reduceMotion:v1';

const osReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let messageSeq = 0;
const nextId = () => `${Date.now().toString(36)}_${(messageSeq += 1)}`;

function App() {
  const {
    conversations,
    activeId,
    activeMessages,
    privateMode,
    loadingMessages,
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
  } = useConversations();
  const { notify } = useToast();

  const [view, setView] = useState('assistant');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [thinking, setThinking] = useState(false);
  const [streamingMsg, setStreamingMsg] = useState(null);
  const [backendOnline, setBackendOnline] = useState(null);
  const [status, setStatus] = useState(null);
  const [reduceMotion, setReduceMotion] = useState(() => {
    try {
      return localStorage.getItem(MOTION_KEY) === '1';
    } catch {
      return false;
    }
  });

  const chatEndRef = useRef(null);
  const composerRef = useRef(null);
  const inFlightRef = useRef(false);
  const abortRef = useRef(null);
  const streamTimerRef = useRef(null);

  const messages = activeMessages;
  const aiStatus = deriveAiStatus(status, backendOnline);
  const busy = thinking || Boolean(streamingMsg);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('reduce-motion', reduceMotion);
    try {
      localStorage.setItem(MOTION_KEY, reduceMotion ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [reduceMotion]);

  useEffect(() => {
    if (migrationInfo?.imported) {
      notify(`Imported ${migrationInfo.imported} saved conversation${migrationInfo.imported === 1 ? '' : 's'}.`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [migrationInfo]);

  const loadStatus = useCallback((signal) => {
    return getStatus(signal)
      .then((s) => {
        setStatus(s);
        setBackendOnline(true);
        return s;
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return null;
        setBackendOnline(false);
        return null;
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadStatus(controller.signal);
    return () => controller.abort();
  }, [loadStatus]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
      window.clearTimeout(streamTimerRef.current);
    },
    [],
  );

  const cancelActiveTurn = useCallback(() => {
    abortRef.current?.abort();
    window.clearTimeout(streamTimerRef.current);
    streamTimerRef.current = null;
    inFlightRef.current = false;
    setThinking(false);
    setStreamingMsg(null);
  }, []);

  // NOTE: we intentionally do NOT cancel the active turn on every activeId
  // change. The first message in a new draft creates its conversation mid-turn
  // (which changes activeId); cancelling here would abort that in-flight
  // request. Cancellation happens only on explicit user actions below
  // (selecting another conversation / starting a new one).

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest' });
  }, [messages, thinking, streamingMsg, reduceMotion]);

  const finishTurn = () => {
    inFlightRef.current = false;
    streamTimerRef.current = null;
    composerRef.current?.focus?.();
  };

  const streamAssistant = (data) => {
    const full = String(data?.response ?? '');
    const meta = {
      tool: data?.tool,
      intent: data?.intent,
      taskType: data?.task_type,
      executionTime: data?.execution_time,
      provider: data?.provider,
      model: data?.model,
    };
    const msgId = data?.message_id || nextId();

    const commit = (text) => {
      setActiveMessages((current) => [
        ...current,
        { id: msgId, role: 'assistant', text, timestamp: 'Now', meta },
      ]);
      setStreamingMsg(null);
      finishTurn();
    };

    if (reduceMotion || osReducedMotion() || full.length <= STREAM_CHUNK) {
      commit(full);
      return;
    }

    setStreamingMsg({ id: msgId, role: 'assistant', text: '', meta });
    let index = 0;
    const step = () => {
      index = Math.min(index + STREAM_CHUNK, full.length);
      const slice = full.slice(0, index);
      if (index < full.length) {
        setStreamingMsg((prev) => (prev ? { ...prev, text: slice } : prev));
        streamTimerRef.current = window.setTimeout(step, STREAM_DELAY);
      } else {
        commit(full);
      }
    };
    streamTimerRef.current = window.setTimeout(step, STREAM_DELAY);
  };

  const runAssistant = async (userText, wasOffline, persistUser) => {
    if (!userText) return;
    inFlightRef.current = true;
    setThinking(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const convId = await ensureConversationId();
      const data = await sendMessage(userText, {
        conversationId: convId,
        isPrivate: privateMode,
        persistUser,
        signal: controller.signal,
      });
      setActiveMessages((current) => current.filter((m) => !m.isError));
      setBackendOnline(true);
      setThinking(false);
      streamAssistant(data);
      if (!privateMode) onTurnPersisted();
      if (wasOffline) loadStatus();
    } catch (err) {
      if (err?.name === 'AbortError') {
        setThinking(false);
        inFlightRef.current = false;
        return;
      }
      setThinking(false);
      inFlightRef.current = false;

      const isConnection = err?.kind === 'network' || err?.kind === 'timeout';
      if (isConnection) setBackendOnline(false);

      const text = isConnection
        ? `Can't reach CHHOTI DON. ${err.message}`
        : `Something went wrong: ${err.message}`;

      setActiveMessages((current) => [
        ...current,
        { id: nextId(), role: 'assistant', text, timestamp: 'Now', isError: true, kind: err?.kind || 'error' },
      ]);
    }
  };

  const submitMessage = (preset) => {
    const content = (preset ?? message).trim();
    if (!content || inFlightRef.current) return;

    const wasOffline = backendOnline === false;
    setActiveMessages((current) => [
      ...current.filter((m) => !m.isError),
      { id: nextId(), role: 'user', text: content, timestamp: 'Now' },
    ]);
    setMessage('');
    runAssistant(content, wasOffline, true);
  };

  const handleRetry = () => {
    if (inFlightRef.current) return;
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUser) return;
    const wasOffline = backendOnline === false;
    setActiveMessages((current) => current.filter((m) => !m.isError));
    // persistUser=false so the retry does not duplicate the user message.
    runAssistant(lastUser.text, wasOffline, false);
  };

  const handleStop = () => {
    cancelActiveTurn();
    notify('Generation stopped.');
    composerRef.current?.focus?.();
  };

  const handleDismiss = (id) => {
    setActiveMessages((current) => current.filter((m) => m.id !== id));
  };

  const handleNewConversation = () => {
    cancelActiveTurn();
    setMessage('');
    setView('assistant');
    newDraft();
    setSidebarOpen(false);
    requestAnimationFrame(() => composerRef.current?.focus?.());
  };

  const handleSelectConversation = (id) => {
    if (id === activeId) {
      setView('assistant');
      setSidebarOpen(false);
      return;
    }
    // Switching to a different conversation cancels any in-progress turn.
    cancelActiveTurn();
    selectConversation(id);
    setView('assistant');
    setSidebarOpen(false);
  };

  const handleSelectView = (nextView) => {
    setView(nextView);
    setSidebarOpen(false);
  };

  const handlePickPrompt = (idea) => {
    setMessage(idea);
    composerRef.current?.focus?.();
  };

  const handleRename = async (id) => {
    const current = conversations.find((c) => c.id === id);
    const next = window.prompt('Rename conversation', current?.title || '');
    if (next == null) return;
    const trimmed = next.trim();
    if (!trimmed) return;
    try {
      await renameConversation(id, trimmed);
      notify('Conversation renamed.');
    } catch {
      notify('Could not rename conversation.');
    }
  };

  const handleDelete = async (id) => {
    const current = conversations.find((c) => c.id === id);
    if (!window.confirm(`Delete "${current?.title || 'this conversation'}"? This cannot be undone.`)) return;
    try {
      await removeConversation(id);
      notify('Conversation deleted.');
    } catch {
      notify('Could not delete conversation.');
    }
  };

  const handleSearch = (query) => refresh(query);

  const handleClearMemory = async () => {
    if (!window.confirm('Clear the assistant’s short-term memory? Saved conversations are kept.')) return;
    try {
      await resetMemory();
      notify('Short-term memory cleared.');
    } catch {
      notify('Could not clear memory.');
    }
    setSettingsOpen(false);
  };

  const hasConversation = messages.length > 0 || Boolean(streamingMsg) || thinking;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050308] text-slate-100 selection:bg-rose-300/25 selection:text-rose-50">
      <AmbientBackground />
      <CursorTrail />

      <div className="relative z-10 flex min-h-screen gap-3 p-3">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          currentView={view}
          onSelectView={handleSelectView}
          conversations={conversations}
          activeConversationId={activeId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onOpenSettings={() => setSettingsOpen(true)}
          onSearch={handleSearch}
          onRenameConversation={handleRename}
          onDeleteConversation={handleDelete}
        />

        <main className="glass-panel flex min-w-0 flex-1 flex-col overflow-hidden rounded-[28px]">
          <TopBar
            onOpenSidebar={() => setSidebarOpen(true)}
            currentView={view}
            aiStatus={aiStatus}
            privateMode={privateMode}
            desktop={isDesktop()}
            onTogglePrivate={() => {
              const next = !privateMode;
              setPrivateMode(next);
              notify(next ? 'Private mode on — new messages stay in memory only.' : 'Private mode off — conversations are saved.');
            }}
            onOpenSettings={() => setSettingsOpen(true)}
            onThemeClick={() => notify('Light theme is coming soon.')}
          />

          <section className="relative flex min-h-0 flex-1 flex-col">
            <div className="scrollbar-subtle flex-1 overflow-y-auto px-3 pb-8 pt-6 sm:px-6 lg:px-10">
              <div className="mx-auto max-w-4xl">
                {view === 'memory' && <MemoryView onClearMemory={handleClearMemory} />}
                {view === 'workspace' && <WorkspaceView />}
                {view === 'system' && <SystemStatusView status={status} backendOnline={backendOnline} onRefreshStatus={() => loadStatus()} />}
                {view === 'cyber' && <CyberView />}
                {view === 'healing' && <HealingView />}
                {view === 'assistant' &&
                  (!hasConversation ? (
                    <div className="mt-6">
                      {loadingMessages ? (
                        <div className="space-y-3" aria-busy="true">
                          {[0, 1, 2].map((i) => (
                            <div key={i} className="h-16 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.03]" />
                          ))}
                        </div>
                      ) : (
                        <EmptyState backendOnline={backendOnline} prompts={promptIdeas} onPick={handlePickPrompt} />
                      )}
                    </div>
                  ) : (
                    <div
                      className="space-y-5"
                      role="log"
                      aria-live="polite"
                      aria-relevant="additions text"
                      aria-label="Conversation with Chhoti Don"
                    >
                      {messages.map((item) => (
                        <ChatMessage
                          key={item.id}
                          role={item.role}
                          timestamp={item.timestamp}
                          isError={item.isError}
                          onRetry={item.isError ? handleRetry : undefined}
                          onDismiss={item.isError ? () => handleDismiss(item.id) : undefined}
                        >
                          {item.text}
                        </ChatMessage>
                      ))}
                      {streamingMsg && (
                        <ChatMessage role="assistant" timestamp="Now">
                          {streamingMsg.text}
                        </ChatMessage>
                      )}
                      {thinking && <ThinkingIndicator />}
                      <div ref={chatEndRef} />
                    </div>
                  ))}
              </div>
            </div>

            {view === 'assistant' && (
              <div className="relative shrink-0 px-3 pb-3 sm:px-6 sm:pb-5 lg:px-10">
                <div className="pointer-events-none absolute inset-x-0 -top-16 h-20 bg-gradient-to-t from-[#07040b]/85 to-transparent" />
                <ChatComposer
                  value={message}
                  onChange={setMessage}
                  onSubmit={() => submitMessage()}
                  onStop={handleStop}
                  busy={busy}
                  disabled={busy}
                  inputRef={composerRef}
                />
              </div>
            )}
          </section>
        </main>
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        status={status}
        backendOnline={backendOnline}
        desktop={isDesktop()}
        onRefreshStatus={() => loadStatus()}
        reduceMotion={reduceMotion}
        onToggleReduceMotion={setReduceMotion}
        onClearMemory={handleClearMemory}
      />
    </div>
  );
}

export default App;
