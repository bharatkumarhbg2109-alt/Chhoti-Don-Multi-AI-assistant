import React, { useEffect, useRef, useState } from 'react';
import AmbientBackground from './components/AmbientBackground';
import AiOrb from './components/AiOrb';
import ChatComposer from './components/ChatComposer';
import ChatMessage from './components/ChatMessage';
import CursorTrail from './components/CursorTrail';
import Icon from './components/Icon';
import Sidebar from './components/Sidebar';
import ThinkingIndicator from './components/ThinkingIndicator';
import TopBar from './components/TopBar';

const initialMessages = [
  {
    id: 1,
    role: 'assistant',
    text: "Good evening, Bharat. Chhoti Don is fully online and your private workspace is synchronized. What would you like to create, analyze, or plan today?",
    timestamp: 'Now',
  },
  {
    id: 2,
    role: 'user',
    text: 'Help me organize today around study, development work, and one important personal goal.',
    timestamp: 'Now',
  },
  {
    id: 3,
    role: 'assistant',
    text: 'I’ll structure it as three focused blocks: a high-energy study sprint, a protected development session, and one small personal win. I can also convert the plan into a timed checklist once you share your available hours.',
    timestamp: 'Now',
  },
];

const promptIdeas = [
  'Plan my most productive day',
  'Review a technical architecture',
  'Turn notes into a study roadmap',
];

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState(initialMessages);
  const [thinking, setThinking] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages, thinking]);

  const submitMessage = (preset) => {
    const content = (preset ?? message).trim();
    if (!content || thinking) return;

    setMessages((current) => [
      ...current,
      { id: Date.now(), role: 'user', text: content, timestamp: 'Now' },
    ]);
    setMessage('');
    setThinking(true);

    window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: `I’ve mapped “${content}” into a focused execution path. The next best step is to define the outcome, remove non-essential work, and turn the remaining actions into a short sequence with clear checkpoints.`,
          timestamp: 'Now',
        },
      ]);
      setThinking(false);
    }, 1500);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050308] text-slate-100 selection:bg-rose-300/25 selection:text-rose-50">
      <AmbientBackground />
      <CursorTrail />

      <div className="relative z-10 flex min-h-screen gap-3 p-3">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <main className="glass-panel flex min-w-0 flex-1 flex-col overflow-hidden rounded-[28px]">
          <TopBar onOpenSidebar={() => setSidebarOpen(true)} />

          <section className="relative flex min-h-0 flex-1 flex-col">
            <div className="scrollbar-subtle flex-1 overflow-y-auto px-3 pb-8 pt-6 sm:px-6 lg:px-10">
              <div className="mx-auto max-w-4xl">
                <div className="mb-8 flex flex-col items-center text-center">
                  <AiOrb compact thinking={thinking} />
                  <div className="mt-5 flex items-center gap-2 rounded-full border border-rose-200/10 bg-gradient-to-r from-white/[0.04] to-rose-400/[0.025] px-3 py-1.5 backdrop-blur-xl">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-300 opacity-55" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-200 shadow-[0_0_10px_rgba(253,164,175,.7)]" />
                    </span>
                    <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
                      Chhoti Don online
                    </span>
                  </div>
                  <h2 className="font-display mt-4 bg-gradient-to-r from-white via-rose-100 to-fuchsia-200 bg-clip-text text-2xl font-semibold tracking-tight text-transparent sm:text-3xl">
                    Your intelligence. Your command.
                  </h2>
                  <p className="mt-2 max-w-xl text-xs leading-5 text-slate-500 sm:text-sm">
                    A private, adaptive space for learning, building, planning, and making confident decisions.
                  </p>
                </div>

                <div className="space-y-5">
                  {messages.map((item) => (
                    <ChatMessage key={item.id} role={item.role} timestamp={item.timestamp}>
                      {item.text}
                    </ChatMessage>
                  ))}
                  {thinking && <ThinkingIndicator />}
                  <div ref={chatEndRef} />
                </div>

                {!thinking && (
                  <div className="mt-7 flex flex-wrap justify-center gap-2">
                    {promptIdeas.map((idea) => (
                      <button
                        type="button"
                        key={idea}
                        onClick={() => submitMessage(idea)}
                        className="group flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-2 text-[11px] text-slate-400 backdrop-blur-xl transition duration-300 hover:scale-[1.02] hover:border-rose-300/20 hover:bg-rose-300/[0.055] hover:text-rose-100"
                      >
                        <Icon
                          name="sparkles"
                          className="h-3.5 w-3.5 text-fuchsia-300 transition group-hover:text-rose-300"
                        />
                        {idea}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="relative shrink-0 px-3 pb-3 sm:px-6 sm:pb-5 lg:px-10">
              <div className="pointer-events-none absolute inset-x-0 -top-16 h-20 bg-gradient-to-t from-[#07040b]/85 to-transparent" />
              <ChatComposer
                value={message}
                onChange={setMessage}
                onSubmit={() => submitMessage()}
                disabled={thinking}
              />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
