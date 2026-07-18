import React, { useCallback, useEffect, useRef, useState } from 'react';
import AmbientBackground from './components/AmbientBackground';
import ChatComposer from './components/ChatComposer';
import ChatMessage from './components/ChatMessage';
import CursorTrail from './components/CursorTrail';
import EmptyState from './components/EmptyState';
import MemoryView from './components/MemoryView';
import SettingsModal from './components/SettingsModal';
import Sidebar from './components/Sidebar';
import ThinkingIndicator from './components/ThinkingIndicator';
import TopBar from './components/TopBar';
import WorkspaceView from './components/WorkspaceView';
import useConversations from './hooks/useConversations';
import { useToast } from './context/ToastContext';
import { getStatus, sendMessage } from './services/chatApi';
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
    activeConversation,
    activeId,
    privateMode,
    setPrivateMode,
    createConversation,
    selectConversation,
    updateActiveMessages,
    clearAllConversations,
  } = useConversations();
  const { notify } = useToast();

  const [view, setView] = useState('assistant');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [thinking, setThinking] = useState(false);
  const [streamingMsg, setStreamingMsg] = useState(null); // transient assistant message being typed
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

  const messages = activeConversation?.messages ?? [];
  const aiStatus = deriveAiStatus(status, backendOnline);
  const busy = thinking || Boolean(streamingMsg);

  // Apply reduce-motion preference to the document + persist it.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('reduce-motion', reduceMotion);
    try {
      localStorage.setItem(MOTION_KEY, reduceMotion ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [reduceMotion]);

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

  // One-shot status check on mount (no aggressive polling).
  useEffect(() => {
    const controller = new AbortController();
    loadStatus(controller.signal);
    return () => controller.abort();
  }, [loadStatus]);

  // Cancel any in-flight request / typewriter on unmount.
  useEffect(
    () => () => {
      abortRef.current?.abort();
      window.clearTimeout(streamTimerRef.current);
    },
    [],
  );

  // Switching conversations cancels the active turn (aborts are not failures).
  const cancelActiveTurn = useCallback(() => {
    abortRef.current?.abort();
    window.clearTimeout(streamTimerRef.current);
    streamTimerRef.current = null;
    inFlightRef.current = false;
    setThinking(false);
    setStreamingMsg(null);
  }, []);

  useEffect(() => {
    // When the active conversation changes, stop anything in progress.
    cancelActiveTurn();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

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
    };
    const msgId = nextId();

    const commit = (text) => {
      // Commit the finished assistant message and clear the transient in one batch.
      updateActiveMessages((current) => [
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

  const runAssistant = async (userText, wasOffline) => {
    if (!userText) return;
    inFlightRef.current = true;
    setThinking(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const data = await sendMessage(userText, 'chat', controller.signal);
      // Success: clear any stale error bubbles + mark backend online.
      updateActiveMessages((current) => current.filter((m) => !m.isError));
      setBackendOnline(true);
      setThinking(false);
      streamAssistant(data);
      if (wasOffline) loadStatus(); // refresh provider status after recovery
    } catch (err) {
      if (err?.name === 'AbortError') {
        // Cancelled (e.g. conversation switch) — not a failure.
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

      updateActiveMessages((current) => [
        ...current,
        { id: nextId(), role: 'assistant', text, timestamp: 'Now', isError: true, kind: err?.kind || 'error' },
      ]);
    }
  };

  const submitMessage = (preset) => {
    const content = (preset ?? message).trim();
    if (!content || inFlightRef.current) return; // duplicate-submit prevention

    const wasOffline = backendOnline === false;
    // Add the user message and drop any prior error bubbles for a clean turn.
    updateActiveMessages((current) => [
      ...current.filter((m) => !m.isError),
      { id: nextId(), role: 'user', text: content, timestamp: 'Now' },
    ]);
    setMessage('');
    runAssistant(content, wasOffline);
  };

  const handleRetry = () => {
    if (inFlightRef.current) return;
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUser) return;
    const wasOffline = backendOnline === false;
    updateActiveMessages((current) => current.filter((m) => !m.isError));
    runAssistant(lastUser.text, wasOffline);
  };

  const handleDismiss = (id) => {
    updateActiveMessages((current) => current.filter((m) => m.id !== id));
  };

  const handleNewConversation = () => {
    cancelActiveTurn();
    setMessage('');
    setView('assistant');
    createConversation();
    setSidebarOpen(false);
    requestAnimationFrame(() => composerRef.current?.focus?.());
  };

  const handleSelectConversation = (id) => {
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

  const handleClearHistory = () => {
    if (!window.confirm('Clear all locally saved CHHOTI DON conversations? This cannot be undone.')) return;
    cancelActiveTurn();
    clearAllConversations();
    setSettingsOpen(false);
    setView('assistant');
    notify('Local conversation history cleared.');
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
          onClearHistory={handleClearHistory}
        />

        <main className="glass-panel flex min-w-0 flex-1 flex-col overflow-hidden rounded-[28px]">
          <TopBar
            onOpenSidebar={() => setSidebarOpen(true)}
            currentView={view}
            aiStatus={aiStatus}
            privateMode={privateMode}
            onTogglePrivate={() => {
              const next = !privateMode;
              setPrivateMode(next);
              notify(next ? 'Private mode on — new messages stay in memory only.' : 'Private mode off — conversations are saved locally.');
            }}
            onOpenSettings={() => setSettingsOpen(true)}
            onThemeClick={() => notify('Light theme is coming soon.')}
          />

          <section className="relative flex min-h-0 flex-1 flex-col">
            <div className="scrollbar-subtle flex-1 overflow-y-auto px-3 pb-8 pt-6 sm:px-6 lg:px-10">
              <div className="mx-auto max-w-4xl">
                {view === 'memory' && <MemoryView />}
                {view === 'workspace' && <WorkspaceView />}
                {view === 'assistant' &&
                  (!hasConversation ? (
                    <div className="mt-6">
                      <EmptyState backendOnline={backendOnline} prompts={promptIdeas} onPick={handlePickPrompt} />
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
        onRefreshStatus={() => loadStatus()}
        reduceMotion={reduceMotion}
        onToggleReduceMotion={setReduceMotion}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
}

export default App;
