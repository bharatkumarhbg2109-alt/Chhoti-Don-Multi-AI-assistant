import React, { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { useToast } from '../context/ToastContext';
import { transcribeAudio } from '../services/chatApi';

export default function ChatComposer({
  value, onChange, onSubmit, onStop, busy = false, disabled, inputRef, onAttachImage,
}) {
  const localRef = useRef(null);
  const textareaRef = inputRef ?? localRef;
  const fileRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const { notify } = useToast();

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, 144)}px`;
  }, [value]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  };

  // ── Attach image -> vision ──────────────────────────────────
  const onFile = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      notify('Only image files are supported.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => onAttachImage?.(reader.result, file.name);
    reader.onerror = () => notify('Could not read that image.');
    reader.readAsDataURL(file);
  };

  // ── Voice input -> local Whisper transcription ──────────────
  const finishRecording = async () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    chunksRef.current = [];
    if (!blob.size) return;
    setTranscribing(true);
    try {
      const { text } = await transcribeAudio(blob);
      if (text && text.trim()) {
        onChange((value ? `${value} ` : '') + text.trim());
        textareaRef.current?.focus();
      } else {
        notify('Didn’t catch that — please try again.');
      }
    } catch (err) {
      notify(`Transcription failed: ${err?.message || 'error'}`);
    } finally {
      setTranscribing(false);
    }
  };

  const toggleVoice = async () => {
    if (transcribing) return;
    if (recording) {
      setRecording(false);
      try { mediaRecorderRef.current?.stop(); } catch { /* ignore */ }
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
      mr.onstop = finishRecording;
      mediaRecorderRef.current = mr;
      mr.start();
      setRecording(true);
    } catch {
      notify('Microphone access denied. Allow it in your browser settings.');
    }
  };

  const micLabel = recording ? 'Stop recording' : transcribing ? 'Transcribing…' : 'Use voice input';

  return (
    <div className="relative mx-auto w-full max-w-4xl">
      <div className="composer-glow absolute -inset-px rounded-[26px] opacity-0 blur-md transition duration-500" />
      <div className="composer relative flex items-end gap-2 rounded-[25px] border border-white/10 bg-[#032f30]/75 p-2 shadow-[0_18px_60px_rgba(0,0,0,.38)] backdrop-blur-2xl transition duration-300 focus-within:border-brand-300/30 focus-within:bg-[#031716]/90">
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="icon-button mb-0.5 shrink-0"
          aria-label="Attach image"
          title="Attach an image (vision)"
        >
          <Icon name="attachment" className="h-[18px] w-[18px]" />
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Chhoti Don anything..."
          className="max-h-36 min-h-[42px] flex-1 resize-none bg-transparent px-1 py-2.5 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 disabled:cursor-not-allowed"
          aria-label="Message Chhoti Don"
        />

        <button
          type="button"
          onClick={toggleVoice}
          className={`icon-button mb-0.5 shrink-0 ${recording ? 'text-red-400 animate-pulse' : ''} ${transcribing ? 'opacity-50' : ''}`}
          aria-label={micLabel}
          title={micLabel}
        >
          <Icon name="mic" className="h-[18px] w-[18px]" />
        </button>
        {busy && onStop ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="group mb-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-brand-mist-300/40 bg-gradient-to-br from-brand-mist-400/30 to-brand-500/25 text-brand-mist-50 shadow-brand transition duration-300 hover:scale-105 hover:border-brand-mist-200/60"
          >
            <Icon name="stop" className="h-[16px] w-[16px]" />
          </button>
        ) : (
          <button
            type="button"
            disabled={disabled || !value.trim()}
            onClick={onSubmit}
            aria-label="Send message"
            className="interactive group mb-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-brand-300/25 bg-gradient-to-br from-brand-400/35 via-brand-deep-500/30 to-brand-blue-600/35 text-brand-50 shadow-brand hover:border-brand-200/55 hover:shadow-[0_0_40px_rgba(12,150,156,.30)] disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:scale-100"
          >
            <Icon name="send" className="h-[18px] w-[18px] transition-transform duration-300 group-hover:translate-x-0.5" />
          </button>
        )}
      </div>
      <p className="mt-2 text-center text-[10px] text-slate-600">
        {recording ? 'Listening… tap the mic again to stop.'
          : transcribing ? 'Transcribing your voice…'
          : 'Chhoti Don can make mistakes. Verify important information.'}
      </p>
    </div>
  );
}
