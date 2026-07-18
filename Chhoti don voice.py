"""
╔═══════════════════════════════════════╗
║     CHHOTI DON — VOICE CONTROLLER    ║
║     Voice → AI → Speech Pipeline     ║
╚═══════════════════════════════════════╝

Dependencies install karo pehle:
    pip install speechrecognition pyttsx3 requests pyaudio

PyAudio Windows ke liye:
    pip install pipwin
    pipwin install pyaudio
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import speech_recognition as sr
import pyttsx3
import requests
import json
import time
import re
from datetime import datetime


# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
GENERAL_MODEL = "llama3"
CODING_MODEL = "deepseek-coder-v2:lite"

# Keywords jo coding/hacking task detect karein
CODING_KEYWORDS = [
    "code", "script", "function", "program", "python", "javascript",
    "html", "css", "bug", "fix", "error", "debug", "write", "create",
    "build", "develop", "algorithm", "class", "loop", "array", "api",
    "karo", "banao", "likho", "coding", "likhna", "banana"
]


# ─────────────────────────────────────────
#  MODEL ROUTER — Kaun sa model use hoga?
# ─────────────────────────────────────────
def detect_model(text: str) -> str:
    text_lower = text.lower()
    for keyword in CODING_KEYWORDS:
        if keyword in text_lower:
            return CODING_MODEL
    return GENERAL_MODEL


# ─────────────────────────────────────────
#  OLLAMA API CALL
# ─────────────────────────────────────────
def ask_ollama(prompt: str, model: str) -> str:
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "Koi response nahi mila.")
        else:
            return f"Ollama error: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Ollama server nahi mila! 'ollama serve' run karo pehle."
    except Exception as e:
        return f"Error: {str(e)}"


# ─────────────────────────────────────────
#  TEXT TO SPEECH
# ─────────────────────────────────────────
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 175)
        self.engine.setProperty('volume', 0.9)
        voices = self.engine.getProperty('voices')
        # Female voice prefer karo agar available ho
        for v in voices:
            if 'female' in v.name.lower() or 'zira' in v.name.lower():
                self.engine.setProperty('voice', v.id)
                break

    def speak(self, text: str):
        # Code blocks ko skip karo TTS mein
        clean = re.sub(r'```[\s\S]*?```', 'Code block generated.', text)
        clean = re.sub(r'`[^`]+`', '', clean)
        clean = re.sub(r'[#*_]', '', clean)
        clean = clean.strip()
        if clean:
            self.engine.say(clean)
            self.engine.runAndWait()


# ─────────────────────────────────────────
#  MAIN GUI APP
# ─────────────────────────────────────────
class ChhotiDonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ Chhoti Don — Voice Controller")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        self.root.configure(bg="#0a0a0f")

        self.recognizer = sr.Recognizer()
        self.voice_engine = VoiceEngine()
        self.is_listening = False
        self.is_processing = False

        self._setup_styles()
        self._build_ui()
        self._check_ollama_status()

    # ── STYLES ──────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Cyber.TFrame",
            background="#0a0a0f"
        )
        style.configure(
            "Status.TLabel",
            background="#0a0a0f",
            foreground="#00ffff",
            font=("Consolas", 10)
        )
        style.configure(
            "Model.TLabel",
            background="#111122",
            foreground="#00ff88",
            font=("Consolas", 10, "bold"),
            padding=4
        )

    # ── UI BUILD ─────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg="#0d0d1a", height=70)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="◈  CHHOTI DON  ◈",
            font=("Consolas", 20, "bold"),
            fg="#00ffff", bg="#0d0d1a"
        ).pack(side=tk.LEFT, padx=20, pady=15)

        tk.Label(
            header,
            text="VOICE INTELLIGENCE SYSTEM",
            font=("Consolas", 9),
            fg="#004466", bg="#0d0d1a"
        ).pack(side=tk.LEFT, padx=0, pady=22)

        # Ollama status
        self.status_dot = tk.Label(
            header,
            text="⬤  CHECKING...",
            font=("Consolas", 10),
            fg="#ffaa00", bg="#0d0d1a"
        )
        self.status_dot.pack(side=tk.RIGHT, padx=20)

        # ── Model Indicator ──
        model_bar = tk.Frame(self.root, bg="#111122", height=35)
        model_bar.pack(fill=tk.X)
        model_bar.pack_propagate(False)

        tk.Label(
            model_bar, text="ACTIVE MODEL:",
            font=("Consolas", 9), fg="#446688", bg="#111122"
        ).pack(side=tk.LEFT, padx=15, pady=8)

        self.model_label = tk.Label(
            model_bar, text="── WAITING ──",
            font=("Consolas", 10, "bold"), fg="#00ff88", bg="#111122"
        )
        self.model_label.pack(side=tk.LEFT, padx=5)

        tk.Label(
            model_bar, text="llama3=GENERAL  |  deepseek-coder-v2=CODING",
            font=("Consolas", 8), fg="#223344", bg="#111122"
        ).pack(side=tk.RIGHT, padx=15)

        # ── Chat Display ──
        chat_frame = tk.Frame(self.root, bg="#0a0a0f")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 5))

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            font=("Consolas", 11),
            bg="#080810",
            fg="#c8d8e8",
            insertbackground="#00ffff",
            selectbackground="#003344",
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=15, pady=10,
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # Text tags for colors
        self.chat_display.tag_configure("user", foreground="#00ffff", font=("Consolas", 11, "bold"))
        self.chat_display.tag_configure("ai", foreground="#00ff88", font=("Consolas", 11))
        self.chat_display.tag_configure("system", foreground="#ffaa00", font=("Consolas", 10, "italic"))
        self.chat_display.tag_configure("model_tag", foreground="#ff6b35", font=("Consolas", 9))
        self.chat_display.tag_configure("time", foreground="#334455", font=("Consolas", 9))

        # ── Bottom Input Area ──
        bottom = tk.Frame(self.root, bg="#0d0d1a", height=130)
        bottom.pack(fill=tk.X, padx=0, pady=0)
        bottom.pack_propagate(False)

        # Text input
        input_frame = tk.Frame(bottom, bg="#0d0d1a")
        input_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        self.text_input = tk.Entry(
            input_frame,
            font=("Consolas", 12),
            bg="#111122",
            fg="#00ffff",
            insertbackground="#00ffff",
            relief=tk.FLAT,
            bd=0
        )
        self.text_input.pack(fill=tk.X, ipady=8, padx=(0, 5))
        self.text_input.bind("<Return>", self._on_text_send)

        # Buttons
        btn_frame = tk.Frame(bottom, bg="#0d0d1a")
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        # Mic Button
        self.mic_btn = tk.Button(
            btn_frame,
            text="🎙️  SPEAK",
            font=("Consolas", 12, "bold"),
            bg="#003344", fg="#00ffff",
            activebackground="#005566",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20, pady=8,
            cursor="hand2",
            command=self._toggle_listen
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Send Button
        send_btn = tk.Button(
            btn_frame,
            text="⮕  SEND",
            font=("Consolas", 12, "bold"),
            bg="#002233", fg="#00aa88",
            activebackground="#003344",
            relief=tk.FLAT,
            padx=20, pady=8,
            cursor="hand2",
            command=self._on_text_send
        )
        send_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Clear Button
        clear_btn = tk.Button(
            btn_frame,
            text="✕  CLEAR",
            font=("Consolas", 10),
            bg="#1a0a0a", fg="#ff4444",
            activebackground="#2a1010",
            relief=tk.FLAT,
            padx=15, pady=8,
            cursor="hand2",
            command=self._clear_chat
        )
        clear_btn.pack(side=tk.LEFT)

        # Status bar
        self.status_bar = tk.Label(
            btn_frame,
            text="◈ READY — Bolo ya likho",
            font=("Consolas", 9),
            fg="#334455", bg="#0d0d1a"
        )
        self.status_bar.pack(side=tk.RIGHT, padx=10)

        # Welcome message
        self._add_system_msg("◈ Chhoti Don Voice Controller initialized!")
        self._add_system_msg("◈ Mic button dabao ya type karo — main sun rahi hoon!")

    # ── OLLAMA STATUS CHECK ──────────────────
    def _check_ollama_status(self):
        def check():
            try:
                r = requests.get("http://localhost:11434/", timeout=3)
                if r.status_code == 200:
                    self.root.after(0, lambda: self.status_dot.config(
                        text="⬤  OLLAMA ONLINE", fg="#00ff88"
                    ))
                    self._add_system_msg("◈ Ollama connected! llama3 + deepseek-coder-v2 ready.")
                else:
                    self._set_ollama_offline()
            except:
                self._set_ollama_offline()

        threading.Thread(target=check, daemon=True).start()

    def _set_ollama_offline(self):
        self.root.after(0, lambda: self.status_dot.config(
            text="⬤  OLLAMA OFFLINE", fg="#ff4444"
        ))
        self._add_system_msg("⚠ Ollama nahi mila! CMD mein 'ollama serve' run karo.")

    # ── VOICE LISTEN ────────────────────────
    def _toggle_listen(self):
        if self.is_processing:
            return
        if not self.is_listening:
            self.is_listening = True
            self.mic_btn.config(text="⏹  LISTENING...", bg="#003300", fg="#00ff00")
            self.status_bar.config(text="◈ Microphone active — bolna shuru karo...")
            threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
                self.root.after(0, lambda: self.status_bar.config(text="◈ Processing speech..."))
                text = self.recognizer.recognize_google(audio, language="hi-IN")
                self.root.after(0, lambda: self._process_input(text))
            except sr.WaitTimeoutError:
                self.root.after(0, lambda: self._add_system_msg("⚠ Koi awaaz nahi aayi — dobara try karo."))
            except sr.UnknownValueError:
                self.root.after(0, lambda: self._add_system_msg("⚠ Samajh nahi aaya — thoda clearly bolo."))
            except Exception as e:
                self.root.after(0, lambda: self._add_system_msg(f"⚠ Mic error: {e}"))
            finally:
                self.is_listening = False
                self.root.after(0, lambda: self.mic_btn.config(
                    text="🎙️  SPEAK", bg="#003344", fg="#00ffff"
                ))

    # ── TEXT INPUT ──────────────────────────
    def _on_text_send(self, event=None):
        text = self.text_input.get().strip()
        if text:
            self.text_input.delete(0, tk.END)
            self._process_input(text)

    # ── MAIN PROCESSING ─────────────────────
    def _process_input(self, user_text: str):
        if self.is_processing:
            return
        self.is_processing = True

        model = detect_model(user_text)
        self._add_user_msg(user_text)
        self.model_label.config(text=f"  {model}  ")

        model_type = "🧠 GENERAL" if model == GENERAL_MODEL else "💻 CODING"
        self._add_system_msg(f"◈ Routing to {model_type} — {model}")
        self.status_bar.config(text=f"◈ {model} se puch raha hoon...")
        self.mic_btn.config(state=tk.DISABLED)

        def fetch():
            response = ask_ollama(user_text, model)
            self.root.after(0, lambda: self._handle_response(response))

        threading.Thread(target=fetch, daemon=True).start()

    def _handle_response(self, response: str):
        self._add_ai_msg(response)
        self.status_bar.config(text="◈ Speaking response...")

        def speak():
            self.voice_engine.speak(response)
            self.root.after(0, lambda: self.status_bar.config(text="◈ READY — Bolo ya likho"))
            self.root.after(0, lambda: self.mic_btn.config(state=tk.NORMAL))
            self.is_processing = False

        threading.Thread(target=speak, daemon=True).start()

    # ── CHAT DISPLAY HELPERS ─────────────────
    def _add_user_msg(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"\n[{now}] ", "time")
        self.chat_display.insert(tk.END, "YOU ▶ ", "user")
        self.chat_display.insert(tk.END, f"{text}\n", "user")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _add_ai_msg(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"[{now}] ", "time")
        self.chat_display.insert(tk.END, "CHHOTI DON ▶ ", "ai")
        self.chat_display.insert(tk.END, f"{text}\n", "ai")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _add_system_msg(self, text: str):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{text}\n", "system")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _clear_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self._add_system_msg("◈ Chat cleared. Main phir se ready hoon!")


# ─────────────────────────────────────────
#  LAUNCH
# ─────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = ChhotiDonApp(root)
    root.mainloop()