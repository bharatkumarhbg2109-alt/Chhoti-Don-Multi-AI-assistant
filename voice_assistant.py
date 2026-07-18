"""
Chhoti Don - Voice Assistant
Wake word: "Hey Don"
Language: Hindi/Hinglish
Voice: Microsoft Zira/Heera (SAPI5 Offline)
Run: python voice_assistant.py
"""

import speech_recognition as sr
import threading
import requests
import time
import re
import pyttsx3

# ============================================================
# CONFIGURATION
# ============================================================

WAKE_WORDS = [
    "hey don", "hey dawn", "a don", "hay don", "he don",
    "chhoti don", "aye don", "chhoti bachi", "choti bachi",
    "chhoti bacchi", "choti bacchi", "chhoti", "bacchi", "hey bacchi"
]

# Ollama Models
OLLAMA_MODEL        = "mistral:latest"         # General chat
OLLAMA_CODING_MODEL = "deepseek-coder-v2:lite" # Coding tasks

# Coding keywords — deepseek route hoga
CODING_KEYWORDS = [
    "code", "script", "function", "python", "javascript", "html",
    "css", "bug", "fix", "error", "debug", "banao", "likho",
    "program", "algorithm", "class", "loop", "api", "build",
    "develop", "karo", "likhna", "banana", "syntax"
]

INTERNET_KEYWORDS = [
    "weather", "mausam", "news", "khabar", "search", "dhundho",
    "stock", "price", "cricket", "score", "today", "aaj", "latest",
    "abhi", "current", "live", "temperature", "tapmaan", "forecast",
]

API_URL    = "http://localhost:8000/api/chat"
OLLAMA_URL = "http://localhost:11434/api/generate"


# ============================================================
# COLORS
# ============================================================

class C:
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    PINK   = "\033[95m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


# ============================================================
# VOICE ENGINE — pyttsx3 SAPI5 (Free + Offline)
# ============================================================

class VoiceEngine:
    def __init__(self):
        self.speaking = False
        self.engine = pyttsx3.init('sapi5')
        self._setup()
        print(f"{C.GREEN}✅ Voice: Windows SAPI5 (Offline){C.RESET}")

    def _setup(self):
        voices = self.engine.getProperty('voices')
        selected = None

        for v in voices:
            name = v.name.lower()
            if 'zira' in name:
                selected = v.id
                print(f"{C.GREEN}   Voice: Microsoft Zira (US Female){C.RESET}")
                break
            elif 'heera' in name:
                selected = v.id
                print(f"{C.GREEN}   Voice: Microsoft Heera (Hindi Female){C.RESET}")
                break

        if not selected:
            for v in voices:
                if 'female' in v.name.lower():
                    selected = v.id
                    break

        if selected:
            self.engine.setProperty('voice', selected)
        else:
            if len(voices) > 1:
                self.engine.setProperty('voice', voices[1].id)

        self.engine.setProperty('rate', 175)
        self.engine.setProperty('volume', 1.0)

    def speak(self, text: str):
        if not text or self.speaking:
            return
        self.speaking = True
        clean = re.sub(r'```[\s\S]*?```', 'code block hai', text)
        clean = re.sub(r'[*_#`]', '', clean)[:400]
        print(f"\n{C.PINK}🔊 Don: {clean}{C.RESET}")
        try:
            self.engine.say(clean)
            self.engine.runAndWait()
        except Exception as e:
            print(f"{C.RED}Voice error: {e}{C.RESET}")
        finally:
            self.speaking = False

    def speak_bg(self, text: str):
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t


# ============================================================
# SPEECH LISTENER
# ============================================================
class SpeechListener:
    def __init__(self):
        self.rec = sr.Recognizer()
        self.rec.energy_threshold = 1500
        self.rec.dynamic_energy_threshold = True
        self.rec.pause_threshold = 0.6

        # Sahi mic index try karo
        mic_index = None
        for idx in [1, 5, 18]:
            try:
                test_mic = sr.Microphone(device_index=idx)
                with test_mic as source:
                    self.rec.adjust_for_ambient_noise(source, duration=1)
                mic_index = idx
                print(f"{C.GREEN}✅ Microphone ready! (index {idx}){C.RESET}")
                break
            except Exception as e:
                print(f"{C.YELLOW}   Index {idx} failed: {e}{C.RESET}")
                continue

        if mic_index is None:
            print(f"{C.RED}❌ Koi mic nahi mila! Default use kar raha hoon.{C.RESET}")
            self.mic = sr.Microphone()
        else:
            self.mic = sr.Microphone(device_index=mic_index)

    def listen(self, timeout: int = 5, phrase_limit: int = 10) -> str:
        try:
            with self.mic as source:
                audio = self.rec.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            try:
                return self.rec.recognize_google(audio, language="hi-IN").lower().strip()
            except Exception:
                return self.rec.recognize_google(audio, language="en-IN").lower().strip()
        except Exception:
            return ""


# ============================================================
# PERMISSION MANAGER
# ============================================================

class PermissionManager:
    def __init__(self, voice: VoiceEngine, listener: SpeechListener):
        self.voice = voice
        self.listener = listener

    def needs_internet(self, text: str) -> bool:
        return any(kw in text.lower() for kw in INTERNET_KEYWORDS)

    def ask_permission(self) -> bool:
        self.voice.speak(
            "Iska jawab dene ke liye mujhe internet chahiye. "
            "Kya main internet use kar sakti hoon? Haan ya naa boliye."
        )
        response = self.listener.listen(timeout=8)
        print(f"{C.BLUE}   Permission response: '{response}'{C.RESET}")
        allowed = any(w in response for w in [
            "haan", "han", "yes", "kar", "karo", "bilkul", "theek", "ok", "ha", "ji"
        ])
        if allowed:
            self.voice.speak("Theek hai!")
        else:
            self.voice.speak("Theek hai, internet use nahi karungi.")
        return allowed


# ============================================================
# AI BRAIN — Fixed with proper model routing
# ============================================================

class AIBrain:
    def __init__(self):
        self.memory = []
        self.use_api = self._check_api()
        print(f"{C.GREEN}✅ Brain: {'Flask API' if self.use_api else 'Ollama Direct'}{C.RESET}")

    def _check_api(self) -> bool:
        try:
            return requests.get("http://localhost:8000/api/status", timeout=3).status_code == 200
        except Exception:
            return False

    # ── BUG FIX 1: _detect_model indentation sahi ki ──
    def _detect_model(self, text: str) -> str:
        for kw in CODING_KEYWORDS:
            if kw in text.lower():
                print(f"{C.CYAN}💻 Coding mode → deepseek-coder-v2:lite{C.RESET}")
                return OLLAMA_CODING_MODEL
        print(f"{C.GREEN}🧠 General mode → mistral:latest{C.RESET}")
        return OLLAMA_MODEL

    # ── BUG FIX 2: think() method properly indented inside class ──
    def think(self, question: str) -> str:
        self.memory.append({"role": "user", "content": question})
        if len(self.memory) > 8:
            self.memory.pop(0)

        # BUG FIX 3: model detection call inside method (not outside)
        model = self._detect_model(question)

        if self.use_api:
            try:
                res = requests.post(
                    API_URL,
                    json={"message": question, "tool": "chat"},
                    timeout=30
                )
                if res.status_code == 200:
                    answer = res.json().get("response", "")
                    if answer:
                        self.memory.append({"role": "assistant", "content": answer})
                        return self._clean(answer)
            except Exception:
                pass

        try:
            system = (
                "Tu Chhoti Don hai — ek pyaari helpful AI assistant ladki. "
                "Hinglish mein baat kar. Short jawab de max 2-3 sentences. "
                "Natural aur friendly reh. Voice assistant hai."
            )
            res = requests.post(OLLAMA_URL, json={
                "model": model,   # ← Smart routing yahan hota hai
                "prompt": question,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.75, "num_predict": 150}
            }, timeout=60)
            if res.status_code == 200:
                answer = res.json().get("response", "").strip()
                self.memory.append({"role": "assistant", "content": answer})
                return self._clean(answer)
        except Exception:
            pass

        return "Maafi chahti hoon, abhi jawab nahi de sakti."

    def _clean(self, text: str) -> str:
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'[*_#`]', '', text)
        return '. '.join(text.split('.')[:3]).strip()

    def web_search(self, query: str) -> str:
        try:
            res = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                timeout=10
            )
            data = res.json()
            ans = data.get("AbstractText", "")
            if ans:
                return ans[:250]
            topics = data.get("RelatedTopics", [])
            if topics and isinstance(topics[0], dict):
                return topics[0].get("Text", "")[:250]
        except Exception:
            pass
        return f"Internet se kuch nahi mila '{query}' ke baare mein."

    def get_weather(self, city: str = "Delhi") -> str:
        try:
            res = requests.get(f"https://wttr.in/{city}?format=3", timeout=8)
            if res.status_code == 200:
                return f"{city} ka mausam: {res.text.strip()}"
        except Exception:
            pass
        return "Weather info abhi available nahi hai."


# ============================================================
# MAIN ASSISTANT
# ============================================================

class ChhotiDonVoice:
    def __init__(self):
        print(f"\n{C.BOLD}{C.PINK}{'='*55}{C.RESET}")
        print(f"{C.BOLD}{C.PINK}  🎤 Chhoti Don — Voice Assistant{C.RESET}")
        print(f"{C.BOLD}{C.PINK}  Wake Word : 'Hey Don'{C.RESET}")
        print(f"{C.BOLD}{C.PINK}  Models    : mistral + deepseek-coder-v2{C.RESET}")
        print(f"{C.BOLD}{C.PINK}{'='*55}{C.RESET}\n")

        self.voice    = VoiceEngine()
        self.listener = SpeechListener()
        self.perm     = PermissionManager(self.voice, self.listener)
        self.brain    = AIBrain()
        self.running  = True

    def _is_wake(self, text: str) -> bool:
        return any(ww in text.lower() for ww in WAKE_WORDS)

    def _is_exit(self, text: str) -> bool:
        return any(w in text for w in [
            "band karo", "bye", "exit", "stop", "soja", "alvida", "quit"
        ])

    def _process(self, command: str):
        print(f"\n{C.GREEN}👤 User: {command}{C.RESET}")

        if self._is_exit(command):
            self.voice.speak("Theek hai! Alvida! Phir milenge!")
            self.running = False
            return

        if self.perm.needs_internet(command):
            allowed = self.perm.ask_permission()
            if not allowed:
                return
            if any(w in command for w in ["weather", "mausam", "temperature"]):
                words = command.split()
                city = "Delhi"
                for i, w in enumerate(words):
                    if w in ["in", "mein", "ka", "ki", "of", "at"] and i + 1 < len(words):
                        city = words[i + 1].title()
                        break
                answer = self.brain.get_weather(city)
            else:
                answer = self.brain.web_search(command)
        else:
            self.voice.speak("Hmm, soch rahi hoon...")
            answer = self.brain.think(command)

        if answer:
            self.voice.speak(answer)
        else:
            self.voice.speak("Koi jawab nahi mila, sorry!")

    def run(self):
        self.voice.speak(
            "Namaste! Main Chhoti Don hoon. "
            "Hey Don boliye — main aapki madad ke liye taiyaar hoon!"
        )
        print(f"\n{C.YELLOW}👂 'Hey Don' ka intezaar hai...{C.RESET}")
        print(f"{C.YELLOW}   Band karne ke liye Ctrl+C dabaiye\n{C.RESET}")

        while self.running:
            try:
                print(f"{C.BLUE}💤 Listening... (say 'Hey Don'){C.RESET}", end='\r')
                heard = self.listener.listen(timeout=3, phrase_limit=5)

                if not heard:
                    continue

                if self._is_wake(heard):
                    print(f"\n{C.GREEN}⚡ Wake word suna! '{heard}'{C.RESET}")
                    self.voice.speak("Haan boliye!")
                    print(f"{C.CYAN}🎤 Command sun rahi hoon...{C.RESET}")
                    command = self.listener.listen(timeout=10, phrase_limit=20)

                    if command and len(command) > 2:
                        self._process(command)
                    else:
                        self.voice.speak("Kuch suna nahi, dobara boliye!")

                    print(f"\n{C.YELLOW}👂 Dobara 'Hey Don' boliye...{C.RESET}")

            except KeyboardInterrupt:
                print(f"\n\n{C.YELLOW}Band ho raha hoon...{C.RESET}")
                self.voice.speak("Alvida! Phir milenge!")
                break
            except Exception:
                time.sleep(0.5)
                continue

        print(f"\n{C.PINK}Voice Assistant band ho gaya. 👋{C.RESET}\n")


# ============================================================
# LAUNCH
# ============================================================

if __name__ == "__main__":
    assistant = ChhotiDonVoice()
    assistant.run() 