import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import pyttsx3
import requests
from datetime import datetime
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
GENERAL_MODEL = "llama3"
CODING_MODEL = "deepseek-coder-v2:lite"

CODING_KEYWORDS = [
    "code","script","function","program","python","javascript",
    "html","css","bug","fix","error","debug","write","create",
    "build","develop","algorithm","class","loop","array","api",
    "karo","banao","likho","coding","likhna","banana"
]

def detect_model(text):
    for kw in CODING_KEYWORDS:
        if kw in text.lower():
            return CODING_MODEL
    return GENERAL_MODEL

def ask_ollama(prompt, model):
    try:
        r = requests.post(OLLAMA_URL, json={"model":model,"prompt":prompt,"stream":False}, timeout=120)
        if r.status_code == 200:
            return r.json().get("response","Koi response nahi.")
        return f"Error: {r.status_code}"
    except requests.exceptions.ConnectionError:
        return "Ollama nahi mila! 'ollama serve' run karo."
    except Exception as e:
        return f"Error: {e}"

class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 175)
        self.engine.setProperty('volume', 0.9)
        for v in self.engine.getProperty('voices'):
            if 'female' in v.name.lower() or 'zira' in v.name.lower():
                self.engine.setProperty('voice', v.id)
                break
    def speak(self, text):
        clean = re.sub(r'```[\s\S]*?```','Code block generated.',text)
        clean = re.sub(r'[`#*_]','',clean).strip()
        if clean:
            self.engine.say(clean)
            self.engine.runAndWait()

class ChhotiDonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chhoti Don — Voice Controller")
        self.root.geometry("900x650")
        self.root.configure(bg="#0a0a0f")
        self.recognizer = sr.Recognizer()
        self.voice_engine = VoiceEngine()
        self.is_listening = False
        self.is_processing = False
        self._build_ui()
        self._check_ollama()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#0d0d1a", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="◈  CHHOTI DON — VOICE CONTROLLER  ◈",
            font=("Consolas",16,"bold"), fg="#00ffff", bg="#0d0d1a"
        ).pack(side=tk.LEFT, padx=20, pady=12)
        self.status_dot = tk.Label(header, text="⬤ CHECKING",
            font=("Consolas",10), fg="#ffaa00", bg="#0d0d1a")
        self.status_dot.pack(side=tk.RIGHT, padx=20)

        mbar = tk.Frame(self.root, bg="#111122", height=30)
        mbar.pack(fill=tk.X)
        mbar.pack_propagate(False)
        tk.Label(mbar, text="MODEL:", font=("Consolas",9), fg="#446688", bg="#111122"
        ).pack(side=tk.LEFT, padx=10, pady=6)
        self.model_label = tk.Label(mbar, text="── WAITING ──",
            font=("Consolas",9,"bold"), fg="#00ff88", bg="#111122")
        self.model_label.pack(side=tk.LEFT)

        self.chat = scrolledtext.ScrolledText(self.root,
            font=("Consolas",11), bg="#080810", fg="#c8d8e8",
            insertbackground="#00ffff", relief=tk.FLAT,
            wrap=tk.WORD, padx=12, pady=8, state=tk.DISABLED)
        self.chat.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.chat.tag_configure("user", foreground="#00ffff", font=("Consolas",11,"bold"))
        self.chat.tag_configure("ai", foreground="#00ff88")
        self.chat.tag_configure("sys", foreground="#ffaa00", font=("Consolas",10,"italic"))
        self.chat.tag_configure("time", foreground="#334455", font=("Consolas",9))

        bottom = tk.Frame(self.root, bg="#0d0d1a")
        bottom.pack(fill=tk.X, padx=12, pady=(0,10))
        self.entry = tk.Entry(bottom, font=("Consolas",12),
            bg="#111122", fg="#00ffff", insertbackground="#00ffff", relief=tk.FLAT)
        self.entry.pack(fill=tk.X, ipady=7, pady=(0,6))
        self.entry.bind("<Return>", self._on_send)

        self.mic_btn = tk.Button(bottom, text="🎙️  SPEAK",
            font=("Consolas",11,"bold"), bg="#003344", fg="#00ffff",
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2",
            command=self._toggle_listen)
        self.mic_btn.pack(side=tk.LEFT, padx=(0,8))
        tk.Button(bottom, text="⮕ SEND", font=("Consolas",11,"bold"),
            bg="#002233", fg="#00aa88", relief=tk.FLAT, padx=16, pady=6,
            cursor="hand2", command=self._on_send).pack(side=tk.LEFT, padx=(0,8))
        tk.Button(bottom, text="✕ CLEAR", font=("Consolas",10),
            bg="#1a0a0a", fg="#ff4444", relief=tk.FLAT, padx=12, pady=6,
            cursor="hand2", command=self._clear).pack(side=tk.LEFT)
        self.status_bar = tk.Label(bottom, text="◈ READY",
            font=("Consolas",9), fg="#334455", bg="#0d0d1a")
        self.status_bar.pack(side=tk.RIGHT)

        self._sys("◈ Chhoti Don Voice Controller ready!")
        self._sys("◈ Mic dabao ya type karo — main sun rahi hoon!")

    def _check_ollama(self):
        def chk():
            try:
                r = requests.get("http://localhost:11434/", timeout=3)
                if r.status_code == 200:
                    self.root.after(0, lambda: self.status_dot.config(text="⬤ OLLAMA ONLINE", fg="#00ff88"))
                    self._sys("◈ Ollama connected! llama3 + deepseek ready.")
                else: self._set_offline()
            except: self._set_offline()
        threading.Thread(target=chk, daemon=True).start()

    def _set_offline(self):
        self.root.after(0, lambda: self.status_dot.config(text="⬤ OLLAMA OFFLINE", fg="#ff4444"))
        self._sys("⚠ Ollama nahi mila! 'ollama serve' run karo.")

    def _toggle_listen(self):
        if self.is_processing or self.is_listening: return
        self.is_listening = True
        self.mic_btn.config(text="⏹ LISTENING...", bg="#003300", fg="#00ff00")
        self.status_bar.config(text="◈ Bol raha hoon...")
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        with sr.Microphone() as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=0.5)
            try:
                audio = self.recognizer.listen(src, timeout=8, phrase_time_limit=15)
                text = self.recognizer.recognize_google(audio, language="hi-IN")
                self.root.after(0, lambda: self._process(text))
            except sr.WaitTimeoutError:
                self.root.after(0, lambda: self._sys("⚠ Awaaz nahi aayi — dobara try karo."))
            except sr.UnknownValueError:
                self.root.after(0, lambda: self._sys("⚠ Samajh nahi aaya — clearly bolo."))
            except Exception as e:
                self.root.after(0, lambda: self._sys(f"⚠ Mic error: {e}"))
            finally:
                self.is_listening = False
                self.root.after(0, lambda: self.mic_btn.config(text="🎙️  SPEAK", bg="#003344", fg="#00ffff"))

    def _on_send(self, e=None):
        t = self.entry.get().strip()
        if t:
            self.entry.delete(0, tk.END)
            self._process(t)

    def _process(self, text):
        if self.is_processing: return
        self.is_processing = True
        model = detect_model(text)
        self._add("user", f"YOU ▶ {text}")
        self.model_label.config(text=f" {model} ")
        self._sys(f"◈ Routing → {'💻 CODING' if model==CODING_MODEL else '🧠 GENERAL'}")
        self.mic_btn.config(state=tk.DISABLED)
        self.status_bar.config(text=f"◈ {model} se puch raha hoon...")
        threading.Thread(target=lambda: self._fetch(text, model), daemon=True).start()

    def _fetch(self, text, model):
        resp = ask_ollama(text, model)
        self.root.after(0, lambda: self._respond(resp))

    def _respond(self, resp):
        self._add("ai", f"CHHOTI DON ▶ {resp}")
        self.status_bar.config(text="◈ Speaking...")
        def spk():
            self.voice_engine.speak(resp)
            self.root.after(0, lambda: self.status_bar.config(text="◈ READY"))
            self.root.after(0, lambda: self.mic_btn.config(state=tk.NORMAL))
            self.is_processing = False
        threading.Thread(target=spk, daemon=True).start()

    def _add(self, tag, text):
        now = datetime.now().strftime("%H:%M")
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, f"[{now}] ", "time")
        self.chat.insert(tk.END, f"{text}\n", tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _sys(self, text):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{text}\n", "sys")
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _clear(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete(1.0, tk.END)
        self.chat.config(state=tk.DISABLED)
        self._sys("◈ Chat cleared. Ready hoon!")

if __name__ == "__main__":
    root = tk.Tk()
    ChhotiDonApp(root)
    root.mainloop()