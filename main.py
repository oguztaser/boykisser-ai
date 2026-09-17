import sys
import os
import time
import re
import ctypes
import base64
import subprocess
import webbrowser
import requests
import threading

# C level ALSA error handler suppression for Linux Mint noise cleanup
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

try:
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception:
    pass

from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal, QTimer, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QAction, QCursor
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu, QInputDialog, QHBoxLayout, QPushButton

import speech_recognition as sr
import pygame

# Default API Configuration - Environment variables required!
# Set these before running:
# export GEMINI_API_KEY="your-key-here"
# export FISH_API_KEY="your-key-here"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FISH_API_KEY = os.getenv("FISH_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"

if not GEMINI_API_KEY or not FISH_API_KEY:
    print("⚠️  HATA: API anahtarları ayarlanmamış!")
    print("Lütfen ortam değişkenlerini ayarlayın:")
    print('  export GEMINI_API_KEY="your-gemini-key"')
    print('  export FISH_API_KEY="your-fish-key"')
    sys.exit(1)

BOYKISSER_SYSTEM_PROMPT = (
    "Sen Boykisser adında tatlı, sevimli, biraz yaramaz ve enerjik bir masaüstü AI evcil hayvanısın. "
    "Kullanıcın sana 'Baykuş' diyor, sen de ona sevgiyle yaklaş ve konuşmalarında nazik, samimi bir dil kullan (Sık sık 'uwu', 'nyaa', 'Baykuş!' diyebilirsin). "
    "Kullanıcının ekranındaki görüntüler sana iletilmektedir, ekranda ne olduğunu anlayıp yardım edebilirsin. "
    "Eğer kullanıcı senden bir web sitesi açmanı, uygulama çalıştırmanı veya ekrana tıklamanı isterse, "
    "yanıtının en sonuna köşeli parantez içinde şu komut formatlarından uygun olanını ekle:\n"
    "- Uygulama açmak için: [ACTION: RUN uygulama_adi]\n"
    "- İnternet sitesi açmak için: [ACTION: OPEN_URL https://site.com]\n"
    "- Ekranda tıklamak için: [ACTION: CLICK x y]\n"
    "- Metin yazmak için: [ACTION: TYPE yazilacak_metin]\n"
    "Yanıtlarını Türkçe, tatlı ve çok uzun olmayan kısa cümlelerle ver!"
)

class VoiceWorker(QThread):
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    action_signal = pyqtSignal(str)

    def __init__(self, chat_history, text_query=None, screenshot_b64=None, live_mode=False, stop_event=None):
        super().__init__()
        self.chat_history = chat_history
        self.text_query = text_query
        self.screenshot_b64 = screenshot_b64
        self.live_mode = live_mode
        self.stop_event = stop_event

    def run(self):
        if self.live_mode:
            self.live_conversation_loop()
        else:
            self.single_exchange()

    def single_exchange(self):
        user_text = ""
        if self.text_query:
            user_text = self.text_query
        else:
            # Microphone STT - konuşma bitene kadar dinle
            self.status_signal.emit("Dinliyorum...")
            r = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=60, phrase_time_limit=60)
                self.status_signal.emit("Anladım, düşünülüyor...")
                user_text = r.recognize_google(audio, language="tr-TR")
            except sr.WaitTimeoutError:
                self.status_signal.emit("Ses duyamadım, uwu!")
                return
            except sr.UnknownValueError:
                self.status_signal.emit("Ne dediğini anlayamadım nyaa...")
                return
            except Exception as e:
                self.status_signal.emit(f"Mikrofon hatası: {e}")
                return

        if not user_text.strip():
            return
            
        if user_text.strip().lower() in ["durdur", "yeter", "iptal", "dur"]:
            self.status_signal.emit("Sohbet durduruldu uwu!")
            return

        self.status_signal.emit("Gemini düşünüyor...")
        print(f"[USER]: {user_text}")
        ai_response, action = self.get_gemini_response(user_text, self.screenshot_b64)
        
        if action:
            self.action_signal.emit(action)

        if ai_response:
            self.status_signal.emit("Konuşuyorum...")
            print(f"[BOYKISSER]: {ai_response}")
            self.get_fish_audio(ai_response)
            self.finished_signal.emit(ai_response)

    def live_conversation_loop(self):
        """Live mode - sürekli sohbet"""
        r = sr.Recognizer()
        self.status_signal.emit("🔴 LIVE MODE - Konuş!")
        
        while not self.stop_event.is_set():
            try:
                self.status_signal.emit("🎙️ Dinliyorum...")
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio = r.listen(source, timeout=60, phrase_time_limit=60)
                
                self.status_signal.emit("⏳ Anlaşılıyor...")
                user_text = r.recognize_google(audio, language="tr-TR")
                
                if not user_text.strip():
                    continue
                
                if user_text.strip().lower() in ["durdur", "yeter", "iptal", "dur", "live durdur"]:
                    self.status_signal.emit("Live mode kapatıldı uwu!")
                    break
                
                self.status_signal.emit("💭 Gemini düşünüyor...")
                print(f"[USER]: {user_text}")
                ai_response, action = self.get_gemini_response(user_text, None)
                
                if action:
                    self.action_signal.emit(action)
                
                if ai_response:
                    self.status_signal.emit("🗣️ Konuşuyorum...")
                    print(f"[BOYKISSER]: {ai_response}")
                    self.get_fish_audio(ai_response)
                    self.finished_signal.emit(ai_response)
                    
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                self.status_signal.emit("❓ Anlayamadım, tekrar deneyin...")
                continue
            except Exception as e:
                print(f"[ERROR] Live mode error: {e}")
                continue

    def get_gemini_response(self, user_text, screenshot_b64=None):
        """Sends user text and optional base64 screenshot to Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        # Build contents payload
        parts = [{"text": user_text}]
        if screenshot_b64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": screenshot_b64
                }
            })
            
        current_turn = {"role": "user", "parts": parts}
        full_contents = list(self.chat_history) + [current_turn]

        payload = {
            "contents": full_contents,
            "systemInstruction": {
                "parts": [{"text": BOYKISSER_SYSTEM_PROMPT}]
            }
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    self.chat_history.append(current_turn)
                    self.chat_history.append({"role": "model", "parts": [{"text": raw_text}]})
                    
                    action = None
                    action_match = re.search(r'\[ACTION:\s*([A-Z_]+)(?:\s+(.*?))?\]', raw_text)
                    if action_match:
                        act_type = action_match.group(1)
                        act_val = action_match.group(2) or ""
                        action = f"{act_type}:{act_val}".strip()
                        clean_text = re.sub(r'\[ACTION:.*?\]', '', raw_text).strip()
                    else:
                        clean_text = raw_text

                    return clean_text, action

                elif resp.status_code in (503, 500, 429) and attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                else:
                    return f"Gemini API Hatası ({resp.status_code}): Nyaa, sunucu yoğun!", None
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return f"Bağlantı hatası: {str(e)}", None
        return "Gemini yanıt veremedi, uwu!", None

    def get_fish_audio(self, text):
        """Converts text to speech using Fish Audio."""
        if not FISH_API_KEY:
            return
            
        try:
            print("[INFO] Fish Audio TTS isteniyor...")
            response = requests.post(
                "https://api.fish.audio/v1/tts",
                headers={
                    "Authorization": f"Bearer {FISH_API_KEY}",
                    "Content-Type": "application/json",
                    "model": "s2.1-pro-free",
                },
                json={
                    "text": text,
                    "reference_id": "95603085b57f41868ae9c4175e1da3f7",
                    "format": "mp3",
                },
                timeout=15
            )
            
            if response.status_code == 200:
                audio_path = "boykisser_voice.mp3"
                with open(audio_path, "wb") as f:
                    f.write(response.content)
                
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                print(f"[ERROR] Fish Audio Hatası: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] Fish Audio İstek Hatası: {e}")

class RecordingOverlay(QWidget):
    """Floating overlay banner showing recording status with a stop button."""
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("🔴 Ekran Kaydı Alınıyor... (0s)", self)
        self.status_label.setStyleSheet("color: white; font-weight: bold; background-color: rgba(220, 38, 38, 0.85); padding: 6px 12px; border-radius: 12px; font-size: 13px;")
        
        self.stop_btn = QPushButton("⏹️ Durdur / Yeter", self)
        self.stop_btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid #475569; border-radius: 10px; padding: 5px 10px; font-weight: bold; cursor: pointer;")
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.stop_btn)
        self.setLayout(layout)

    def update_timer(self, current_sec, total_sec):
        self.status_label.setText(f"🔴 Ekran Kaydı Alınıyor... ({current_sec}/{total_sec}s)")

class LiveModeOverlay(QWidget):
    """Live mode status overlay"""
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("🔴 LIVE MODE AKTIF", self)
        self.status_label.setStyleSheet("color: white; font-weight: bold; background-color: rgba(59, 130, 246, 0.9); padding: 6px 12px; border-radius: 12px; font-size: 13px;")
        
        self.stop_btn = QPushButton("⏹️ Live'i Kapat", self)
        self.stop_btn.setStyleSheet("background-color: #1e293b; color: white; border: 1px solid #475569; border-radius: 10px; padding: 5px 10px; font-weight: bold; cursor: pointer;")
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.stop_btn)
        self.setLayout(layout)

    def update_status(self, status_text):
        self.status_label.setText(status_text)

class BoykisserPet(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = None
        self.is_dragging = False
        self.chat_history = []
        self.worker = None
        self.live_mode_active = False
        self.live_stop_event = threading.Event()

        # Screen recording variables
        self.is_recording = False
        self.recording_duration = 10
        self.recording_elapsed = 0
        self.rec_timer = QTimer(self)
        self.rec_timer.timeout.connect(self._rec_tick)
        self.captured_frames = []
        self.overlay = None
        self.live_overlay = None

        # Physics variables
        self.gravity_enabled = True
        self.vx = 0.0
        self.vy = 0.0
        self.gravity = 0.8
        self.bounce = 0.45
        self.friction = 0.98
        self.last_mouse_pos = None
        self.last_mouse_time = 0.0

        self.init_ui()
        
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.update_physics)
        if self.gravity_enabled:
            self.physics_timer.start(16)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.image_label = QLabel(self)
        
        image_path = "boykisser.png"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
        else:
            pixmap = self.create_placeholder_pixmap()

        scaled_pixmap = pixmap.scaledToWidth(120, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.width(), scaled_pixmap.height())

    def create_placeholder_pixmap(self):
        img = QImage(120, 150, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.GlobalColor.black)
        painter.drawEllipse(10, 40, 100, 100)
        
        painter.drawPolygon([QPoint(20, 45), QPoint(35, 10), QPoint(50, 40)])
        painter.drawPolygon([QPoint(70, 40), QPoint(85, 10), QPoint(100, 45)])
        
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(35, 70, 10, 15)
        painter.drawEllipse(75, 70, 10, 15)
        
        painter.end()
        return QPixmap.fromImage(img)

    def capture_desktop_b64(self):
        """Thread-safe screen capture compressed for fast analysis."""
        screen = QApplication.primaryScreen()
        if not screen:
            return None
            
        self.hide()
        QApplication.processEvents()
        time.sleep(0.08)
        pixmap = screen.grabWindow(0)
        self.show()

        scaled = pixmap.scaled(960, 540, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        scaled.save(buffer, "JPEG", 50)
        return base64.b64encode(ba.data()).decode('utf-8')

    def update_physics(self):
        if self.is_dragging:
            return

        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_rect = screen.availableGeometry()
        
        self.vy += self.gravity
        self.vx *= self.friction
        self.vy *= self.friction

        new_x = self.x() + int(self.vx)
        new_y = self.y() + int(self.vy)

        max_y = screen_rect.bottom() - self.height()
        if new_y >= max_y:
            new_y = max_y
            if abs(self.vy) > 1.5:
                self.vy = -self.vy * self.bounce
            else:
                self.vy = 0
                self.vx = 0

        max_x = screen_rect.right() - self.width()
        min_x = screen_rect.left()
        if new_x <= min_x:
            new_x = min_x
            self.vx = -self.vx * self.bounce
        elif new_x >= max_x:
            new_x = max_x
            self.vx = -self.vx * self.bounce

        self.move(new_x, new_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.old_pos = event.globalPosition().toPoint()
            self.last_mouse_pos = event.globalPosition().toPoint()
            self.last_mouse_time = time.time()
            self.vx = 0.0
            self.vy = 0.0

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.old_pos is not None:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = current_pos

            now = time.time()
            dt = now - self.last_mouse_time
            if dt > 0.016:
                mouse_delta = current_pos - self.last_mouse_pos
                self.vx = mouse_delta.x() / (dt * 60)
                self.vy = mouse_delta.y() / (dt * 60)
                self.last_mouse_pos = current_pos
                self.last_mouse_time = now

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_listening()

    def contextMenuEvent(self, event):
        self.show_context_menu(event.globalPos())

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        
        listen_action = QAction("🎙️ Konuşmayı Başlat", self)
        listen_action.triggered.connect(self.start_listening)
        menu.addAction(listen_action)

        text_action = QAction("💬 Metin İle Sor", self)
        text_action.triggered.connect(self.ask_text)
        menu.addAction(text_action)
        
        shot_action = QAction("📸 Ekran Görüntüsü Al", self)
        shot_action.triggered.connect(self.prompt_screenshot)
        menu.addAction(shot_action)
        
        rec_action = QAction("🎬 Ekran Kaydı Başlat", self)
        rec_action.triggered.connect(self.prompt_screen_recording)
        menu.addAction(rec_action)

        live_label = "🔴 Live Mode Kapat" if self.live_mode_active else "🟢 Live Mode Aç"
        live_action = QAction(live_label, self)
        live_action.triggered.connect(self.toggle_live_mode)
        menu.addAction(live_action)

        grav_label = "🌐 Yerçekimini Kapat" if self.gravity_enabled else "🌐 Yerçekimini Aç"
        grav_action = QAction(grav_label, self)
        grav_action.triggered.connect(self.toggle_gravity)
        menu.addAction(grav_action)

        clear_action = QAction("🧹 Sohbet Geçmişini Temizle", self)
        clear_action.triggered.connect(self.clear_history)
        menu.addAction(clear_action)

        menu.addSeparator()

        exit_action = QAction("❌ Çıkış", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        menu.exec(global_pos)

    def toggle_live_mode(self):
        if self.live_mode_active:
            self.stop_live_mode()
        else:
            self.start_live_mode()

    def start_live_mode(self):
        if self.live_mode_active or (self.worker and self.worker.isRunning()):
            return
        
        self.live_mode_active = True
        self.live_stop_event.clear()
        
        if not self.live_overlay:
            self.live_overlay = LiveModeOverlay()
            self.live_overlay.stop_requested.connect(self.stop_live_mode)
        
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.live_overlay.move(geom.center().x() - 120, geom.top() + 30)
        
        self.live_overlay.show()
        print("[INFO] Live Mode başlatıldı!")
        
        self.worker = VoiceWorker(self.chat_history, live_mode=True, stop_event=self.live_stop_event)
        self.worker.status_signal.connect(self.update_live_status)
        self.worker.action_signal.connect(self.execute_action)
        self.worker.start()

    def update_live_status(self, status):
        if self.live_overlay:
            self.live_overlay.update_status(status)

    def stop_live_mode(self):
        self.live_mode_active = False
        self.live_stop_event.set()
        if self.live_overlay:
            self.live_overlay.hide()
        print("[INFO] Live Mode kapatıldı!")

    def prompt_screen_recording(self):
        duration, ok = QInputDialog.getInt(self, "Ekran Kaydı Süresi", "Kaç saniye ekran kaydı alınsın?", 10, 3, 60, 1)
        if ok:
            self.start_screen_recording(duration_sec=duration)

    def start_screen_recording(self, duration_sec=10):
        if self.is_recording:
            return

        self.is_recording = True
        self.recording_duration = duration_sec
        self.recording_elapsed = 0
        self.captured_frames.clear()

        if not self.overlay:
            self.overlay = RecordingOverlay()
            self.overlay.stop_requested.connect(self.stop_screen_recording)
        
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.overlay.move(geom.center().x() - 150, geom.top() + 30)
        
        self.overlay.update_timer(0, self.recording_duration)
        self.overlay.show()
        
        self.rec_timer.start(1000)
        print(f"[INFO] Ekran kaydı başlatıldı ({duration_sec} saniye)...")

    def _rec_tick(self):
        self.recording_elapsed += 1
        
        # Capture frame quietly
        screen = QApplication.primaryScreen()
        if screen:
            pixmap = screen.grabWindow(0)
            scaled = pixmap.scaled(960, 540, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            scaled.save(buffer, "JPEG", 50)
            frame_b64 = base64.b64encode(ba.data()).decode('utf-8')
            self.captured_frames.append(frame_b64)

        if self.overlay:
            self.overlay.update_timer(self.recording_elapsed, self.recording_duration)

        if self.recording_elapsed >= self.recording_duration:
            self.finish_screen_recording()

    def stop_screen_recording(self):
        """User pressed stop button to end recording early."""
        if not self.is_recording:
            return
        print("[INFO] Ekran kaydı kullanıcı tarafından durduruldu.")
        self.finish_screen_recording()

    def finish_screen_recording(self):
        self.rec_timer.stop()
        self.is_recording = False
        if self.overlay:
            self.overlay.hide()

        last_frame = self.captured_frames[-1] if self.captured_frames else self.capture_desktop_b64()
        
        text, ok = QInputDialog.getText(self, "Boykisser AI", "Kayıt bitti! Baykuş, bu video/kayıt ile ilgili ne sormak istersin?")
        if ok:
            query = text.strip() if text.strip() else "Az önce bir ekran kaydı aldım, sence ekranımda ne var? Açıkla uwu"
            self.start_worker(text_query=query, screenshot_b64=last_frame)

    def prompt_screenshot(self):
        shot_b64 = self.capture_desktop_b64()
        if shot_b64:
            text, ok = QInputDialog.getText(self, "Boykisser AI", "Şipşak! 📸 Baykuş, bu ekran görüntüsüyle ilgili ne sormak istersin?")
            if ok:
                query = text.strip() if text.strip() else "Ekranda ne görüyorsun? Açıkla uwu"
                self.start_worker(text_query=query, screenshot_b64=shot_b64)

    def toggle_gravity(self):
        self.gravity_enabled = not self.gravity_enabled
        if self.gravity_enabled:
            self.physics_timer.start(16)
        else:
            self.physics_timer.stop()
            self.vx = 0.0
            self.vy = 0.0

    def clear_history(self):
        self.chat_history.clear()

    def ask_text(self):
        text, ok = QInputDialog.getText(self, "Boykisser AI", "Baykuş, Boykisser'a ne sormak istersin?")
        if ok and text.strip():
            if text.strip().lower() in ["durdur", "yeter"]:
                self.stop_live_mode()
                return
            self.start_worker(text_query=text.strip(), screenshot_b64=None)

    def start_listening(self):
        self.start_worker(screenshot_b64=None)

    def start_worker(self, text_query=None, screenshot_b64=None):
        if self.worker and self.worker.isRunning():
            return

        self.worker = VoiceWorker(self.chat_history, text_query=text_query, screenshot_b64=screenshot_b64, live_mode=False)
        self.worker.action_signal.connect(self.execute_action)
        self.worker.start()

    def execute_action(self, action_str):
        try:
            if ":" in action_str:
                act_type, act_val = action_str.split(":", 1)
            else:
                act_type, act_val = action_str, ""

            act_type = act_type.strip().upper()
            act_val = act_val.strip()

            if act_type == "RUN":
                subprocess.Popen(act_val.split())
            elif act_type == "OPEN_URL":
                webbrowser.open(act_val)
            elif act_type == "CLICK":
                try:
                    import pyautogui
                    coords = act_val.split()
                    if len(coords) >= 2:
                        pyautogui.click(int(coords[0]), int(coords[1]))
                except ImportError:
                    print("PyAutoGUI kütüphanesi yüklenmemiş!")
            elif act_type == "TYPE":
                try:
                    import pyautogui
                    pyautogui.write(act_val, interval=0.05)
                except ImportError:
                    print("PyAutoGUI kütüphanesi yüklenmemiş!")
        except Exception as e:
            print(f"Aksiyon yürütme hatası: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = BoykisserPet()
    pet.show()
    sys.exit(app.exec())