/** Convert the backend status payload into one truthful UI state. */
export function deriveAiStatus(status, backendOnline) {
  if (backendOnline === false) {
    return { label: 'Backend offline', tone: 'error', detail: 'Cannot reach the server on port 8000.' };
  }
  if (!status) {
    return { label: 'Checking status...', tone: 'muted', detail: 'Contacting the backend.' };
  }

  const mode = status.mode || (status.simulated ? 'simulation' : 'unknown');
  const runtimeMode = status.runtime_mode || mode;
  const model = status.model || 'unknown';

  if (status.provider === 'ollama' && status.provider_online === false) {
    return {
      label: 'Ollama offline',
      tone: 'warn',
      detail: `Backend is online, but Ollama is unavailable. Simulated fallback is active (${model}).`,
    };
  }
  if (status.provider === 'ollama' && status.provider_online && status.model_available === false) {
    return {
      label: 'Model not installed',
      tone: 'warn',
      detail: `Ollama is running but the model "${model}" is not installed. Simulated fallback is active.`,
    };
  }
  if ((mode === 'api' || runtimeMode === 'api') && status.ai_online) {
    return { label: 'Live AI - OpenAI', tone: 'ok', detail: `Using OpenAI model ${model}.` };
  }
  if ((mode === 'live' || mode === 'local') && runtimeMode !== 'api' && status.ai_online) {
    return { label: `Live AI - ${model}`, tone: 'ok', detail: `Using local Ollama model ${model}.` };
  }
  if (mode === 'simulation' || status.simulated) {
    return {
      label: 'Simulated mode',
      tone: 'warn',
      detail: `Real AI is offline; using the built-in fallback (${model}).`,
    };
  }
  return { label: 'Status unknown', tone: 'muted', detail: 'Backend returned an unrecognised mode.' };
}

export const TONE_DOT = {
  ok: 'bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,.7)]',
  warn: 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,.7)]',
  error: 'bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,.7)]',
  muted: 'bg-slate-500',
};
