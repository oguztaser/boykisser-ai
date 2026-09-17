# 🐱 Boykisser AI - Masaüstü Pet

Tatlı, sevimli ve enerjik bir masaüstü AI evcil hayvanı. Konuştur, soru sor, ekran kaydını paylaş!

## Özellikler

- 🎙️ **Ses Kontrolü** - Mikrofon ile doğal konuşma
- 💬 **Metin Girişi** - Yazarak da sorabilirsin
- 📸 **Ekran Görüntüsü** - Ekranı analiz etmesi için göster
- 🎬 **Ekran Kaydı** - Videonu açıklat
- 🟢 **Live Mode** - Kesintisiz sohbet (tuş basma yok!)
- 🎮 **Fizik Motoru** - Ekranda zıplar ve düşer
- 🗣️ **TTS** - Fish Audio ile çok güzel sesler

## Kurulum

### 1. Gerekli Paketler

```bash
pip install PyQt6 SpeechRecognition pygame requests
```

Linux'te speech recognition için:
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

### 2. API Anahtarları Ayarla

**Boykisser'ı çalıştırabilmek için şunlar gerekli:**

1. **Gemini API Key** - https://ai.google.dev
   ```bash
   export GEMINI_API_KEY="your-gemini-key-here"
   ```

2. **Fish Audio API Key** - https://fish.audio
   ```bash
   export FISH_API_KEY="your-fish-key-here"
   ```

**Kalıcı olarak ayarlamak için** (~/.bashrc veya ~/.zshrc'ye ekle):
```bash
echo 'export GEMINI_API_KEY="your-key"' >> ~/.bashrc
echo 'export FISH_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Çalıştır

```bash
python boykisser_live.py
```

## Kullanım

### Sağ Tıkla Menüsü
- **🎙️ Konuşmayı Başlat** - Mikrofon ile konuş (sonuna kadar dinler)
- **💬 Metin İle Sor** - Yazarak sor
- **📸 Ekran Görüntüsü Al** - Screenshotu analiz ettir
- **🎬 Ekran Kaydı Başlat** - Video kaydı başlat
- **🟢 Live Mode Aç** - Kesintisiz sohbet modu
- **🌐 Yerçekimini Aç/Kapat** - Fizik motorunu kapat
- **🧹 Sohbet Geçmişini Temizle** - Chat history sıfırla
- **❌ Çıkış** - Kapat

### Live Mode
Live mode açıldığında:
1. Konuş
2. Boykisser cevapla
3. Tekrar konuş (loop)
4. "durdur", "yeter", "iptal" diye söyle veya Durdur butonuna bas

### Diğer
- **Double-click** - Dinleme başlat
- **Drag** - Taşı (fizik var!)
- **Yer Çekimi** - Açıkken ekranın altına düşer

## Sistem Gereksinimleri

- Python 3.8+
- PyQt6
- Mikrofon
- İnternet bağlantısı
- Linux Mint / Ubuntu / Debian (macOS/Windows'ta da çalışabilir)

## Troubleshooting

**Mikrofon çalışmıyor?**
```bash
python -m speech_recognition
```

**API hataları alıyorsam?**
- Anahtarlarının geçerli olduğundan emin ol
- İnternet bağlantını kontrol et
- API kotanı kontrol et

**Fish Audio ses gelmedi?**
- PyGame kurulu mu? `pip install pygame`
- API keyin geçerli mi?

## API Keyleri Nasıl Alınır?

### Gemini
1. https://ai.google.dev git
2. "Get API Key" butonuna bas
3. Projeyi seç (yeni oluştur gerekirse)
4. Keyi kopyala

### Fish Audio
1. https://fish.audio git
2. Hesap oluştur
3. Dashboard → API → Token oluştur
4. Keyi kopyala

## ⚠️ GÜVENLİK

**API keylerinizi sakla!**
- GitHub'a ASLA push etme
- `.gitignore`'a ekle:
  ```
  .env
  *.key
  ```
- Sadece `.bashrc` / `.zshrc`'de sakla
- Repoyu paylaşırken keylerinizi iptal et

## License

MIT - Özgürce kullan!

## Destek

Hata bulursan issue aç! 🐛

---

**Eğlence veren OğuzCOMPUTER tarafından yapıldı.** hihihihi 👻