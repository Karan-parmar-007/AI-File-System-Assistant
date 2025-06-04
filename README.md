# 🤖 AI File System Assistant

An intelligent file management system that combines **natural language processing**, **voice interaction**, and **real-time file operations** through a sleek Streamlit UI. Talk to your file system, manage files using voice or text commands, and get instant results — built for Windows but conceptually cross-platform.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.31.0-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 🌟 Features

### 💬 Natural Language Processing

- **Conversational Queries**:
  - "Who owns hello_world.txt?"
  - "Show me all Python files"
  - "List files created today"
- **Smart File Operations**:
  - "Create a file named report.txt"
  - "Delete old_file.txt"
  - "Create test.py with content: print('Hello')"

### 🎙️ Voice Interface

- **Speech-to-Text** via Deepgram Nova-2 model
- **Text-to-Speech** with 12 unique AI voices
- **Real-time Transcription & Replies**
- **Custom Recording Duration**: Choose between 3 to 10 seconds

### 📁 File Management

- View:
  - Ownership, timestamps (created, modified, accessed)
  - File attributes: hidden, system, read-only
  - File type and size
- Create:
  - Templates (README, Python, HTML, JSON)
  - Any custom file with user-defined content
- Explore:
  - Interactive file explorer with sorting/filtering
  - Visual indicators for hidden/system files

### 🔧 Technical Highlights

- **Custom C Backend** (`file_lister.c`) for efficient Windows file operations
- **Gemini AI + Deepgram API Integration**
- **Voice + Text Query Handling**
- **Robust Caching and Error Handling**

---

## 📋 Prerequisites

### System

- **Windows 10/11**
- **Python 3.8+**
- **GCC** (MinGW) or Visual Studio for compiling `file_lister.c`
- **Microphone**

### API Keys

Create a `.env` file with the following:

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Optional LiveKit Setup (Future Feature)
LIVEKIT_URL=your_livekit_url_here
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here
```

---

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ai-file-assistant.git
cd ai-file-assistant
```

### 2. Install Dependencies

#### Option A: (Recommended)

```bash
setup.bat
```

#### Option B: Manual Install

```bash
pip install -r requirements.txt
gcc -o file_lister.exe file_lister.c -ladvapi32
```

### 3. Run the App

```bash
streamlit run app.py
```

App launches at: [http://localhost:8501](http://localhost:8501)

---

## 📦 Dependencies

### Python

- `streamlit==1.31.0`
- `google-generativeai==0.3.2`
- `deepgram-sdk==4.1.0`
- `pandas==2.2.0`
- `pyaudio==0.2.14`
- `python-dotenv==1.0.0`

### System

- `file_lister.c` (Windows API calls for metadata)
- MinGW/Visual Studio (for compiling)

---

## 🎯 Usage Examples

### 🔍 Chat

- **Query**: "Show me all text files"
- **Create**: "Create README.md"
- **Delete**: "Remove temp.json"
- **Inspect**: "Who owns hello_world.txt?"

### 🎤 Voice

- Click 🎤 Start Recording
- Speak: "Delete log.txt"
- Auto-transcribed + AI response spoken aloud

### 📁 File Explorer

- Search, sort, and view all files with metadata
- Check ownership, visibility, and timestamps

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│  Voice Assistant │────▶│   Deepgram API  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ SmartFileSystem │────▶│   Gemini AI API  │
│      Tool       │     └──────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  file_lister.c  │
│  (Windows API)  │
└─────────────────┘
```

### Key Modules

- **SmartFileSystemTool**: Handles file I/O, parsing, and AI prompts
- **VoiceAssistant**: Manages audio recording and speech synthesis
- **file_lister.c**: Backend compiled tool to fetch file metadata directly via Windows API

---

## 🛠️ Configuration

### Voice Models (Deepgram)

**Female**:

- Asteria 🇺🇸
- Luna 🇺🇸
- Stella 🇺🇸
- Athena 🇬🇧
- Hera 🇺🇸

**Male**:

- Orion 🇺🇸
- Arcas 🇺🇸
- Perseus 🇺🇸
- Angus 🇮🇪
- Orpheus 🇺🇸
- Helios 🇬🇧
- Zeus 🇺🇸

### File Templates

- Empty file
- Hello World file
- Markdown README
- Python script
- HTML base file
- JSON config file

---

## 🐛 Troubleshooting

### Common Errors

| Issue                  | Solution                                        |
| ---------------------- | ----------------------------------------------- |
| `python not found`   | Ensure Python is in your PATH                   |
| `gcc not recognized` | Install MinGW and add to PATH                   |
| Microphone not working | Check mic permissions and hardware              |
| API errors             | Validate `.env` values and network connection |

### Debug Mode

Check "🔌 API Status" in sidebar to see connectivity status

---

## 📄 License

MIT License. See the LICENSE file.

---

## 🤝 Contributing

PRs welcome!

```bash
git checkout -b feature/AmazingFeature
git commit -m "Add AmazingFeature"
git push origin feature/AmazingFeature
```

Then open a Pull Request.

---

## 📚 References

- [Streamlit Docs](https://docs.streamlit.io/)
- [Google Gemini AI Docs](https://ai.google.dev/)
- [Deepgram API Docs](https://developers.deepgram.com/)
- [Windows API Reference](https://learn.microsoft.com/en-us/windows/win32/api/)

---

## 🙏 Acknowledgments

- Google for the Gemini AI
- Deepgram for STT/TTS
- Streamlit for frontend framework
- The open-source community 🙌

---

> Built with ❤️ using Python, C, and modern AI technologies.
