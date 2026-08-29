# ⚡ Girisha (F.R.I.D.A.Y. & Deep Teaching AI Super-Intelligence)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gemini Live](https://img.shields.io/badge/Gemini_Live-3.1_Flash-orange.svg)](https://ai.google.dev/)
[![Platform Windows](https://img.shields.io/badge/platform-Windows-brightgreen.svg)](#)

**Girisha** is an autonomous, full-duplex speech-to-speech AI companion and super-intelligence (like **F.R.I.D.A.Y. for Tony Stark**). Built with **Google Gemini Multimodal Live API**, she can see your screen in real time, control your laptop, execute code, write files, perform deep web research, and teach university engineering subjects with dynamic visual boards.

---

## 🌟 Key Features

### 🎙️ 1. Native Multimodal Speech-to-Speech
- **Real-time Full Duplex**: Talk to her naturally with low latency without pressing any buttons.
- **Voice Interruption**: Simply speak while she is talking to interrupt and redirect her thoughts.
- **Voice**: Sweet, young, clear, and charming female voice (`Leda`).

### 🖥️ 2. Live Screen Vision (Every 3 Seconds)
- Periodically captures and analyzes your screen in real time.
- Guides you through **LeetCode problems, VS Code errors, online exams, PDF notes, or browser research**.

### 🎓 3. Deep Teaching & Visual Studio (Anna University CSE Syllabus)
- **Visual Studio Canvas (`show_interactive_visual`)**: Automatically pops up interactive **Mermaid flowcharts, architecture diagrams, step-by-step trace tables, and KaTeX math formulas** in your browser.
- **Math & Data Plotting (`generate_math_or_data_plot`)**: Renders matplotlib curves and mathematical simulations directly on screen.
- **Specialized Curriculum**:
  - **Operating Systems (OS)**: Process Scheduling, Semaphores, Banker's Deadlock Algorithm, Paging, Virtual Memory, Disk Scheduling.
  - **Database Management Systems (DBMS)**: Relational Algebra, SQL, Normalization (1NF to BCNF), ACID & 2PL Concurrency.
  - **Data Structures & Algorithms (DSA)**: AVL Trees, Graph Algorithms (Dijkstra, Prim's), Dynamic Programming, LeetCode patterns.
  - **Computer Architecture (CAO)**: 5-Stage MIPS Pipelining, Hazards, Booth's Algorithm, Cache Mapping.

### 💻 4. Autonomous F.R.I.D.A.Y. Laptop Control
- **App & Web Launching**: *"Girisha, open Spotify / VS Code / YouTube."*
- **Terminal Execution**: Runs PowerShell/CMD commands autonomously.
- **WhatsApp Automation**: *"Girisha, open WhatsApp chat [Name]."*
- **Instant Drafting & Typing**: Pastes dictations, emails, or code into active windows.
- **Project File Creator**: Designs and writes complete Python scripts, apps, or HTML files.
- **Self-Evolution**: Can upgrade her own source code on demand.

### 🧠 5. Multi-Session Persistent Memory (SQLite)
- Built-in `girisha_memory.db` stores conversation history, study notes, and user weak spots.
- Auto-retrieves previous conversation context every time you reconnect.

---

## 🚀 Quick Start Guide (For Any Windows Laptop)

### 1. Prerequisites
- **Windows 10 / 11**
- **Python 3.10+** (Ensure **"Add Python to PATH"** is checked during Python installation)
- A **Google Gemini API Key** (Get free from [Google AI Studio](https://aistudio.google.com/))

### 2. Clone the Repository
```bash
git clone https://github.com/Giridharan2029/MyLife.git
cd MyLife
```

### 3. Install Dependencies
Open **Command Prompt** or **PowerShell** in the project folder and run:
```bash
pip install -r requirements.txt

or

# Manually download Girisha Core Dependencies
google-genai>=1.0.0
sounddevice>=0.5.0
numpy>=1.24.0
mss>=9.0.0
pillow>=10.0.0
pyautogui>=0.9.54
pyperclip>=1.8.2
duckduckgo_search>=7.0.0
matplotlib>=3.8.0
fastapi>=0.100.0
uvicorn>=0.22.0
websockets>=12.0
```

---

## ⚡ How to Run Girisha

### Option A: Direct Voice Call in Terminal (Recommended)
Set your Gemini API key and launch the voice system:

#### In Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
python speech_to_speech.py
```

#### In Command Prompt (CMD):
```cmd
set GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
python speech_to_speech.py
```

---

### Option B: Web UI Call Dashboard
If you prefer a visual phone call interface:
1. Start the server:
   ```powershell
   $env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
   python server.py
   ```
2. Open your browser at:
   ```
   http://localhost:8000
   ```

---

### Option C: Silent Background Mode
To keep Girisha running in the background without terminal windows:
- Double-click `launch_silent.vbs` to start.
- Run `stop_girisha.ps1` in PowerShell to stop her anytime.

---

## 🗣️ Example Commands to Try

- **Study & Concept Visualization**:
  - *"Girisha, teach me how Banker's Algorithm works and show a table on my screen."*
  - *"Girisha, show me a flowchart diagram of the 5-stage instruction pipeline."*
  - *"Girisha, plot the curve of $y = x^2 \sin(x)$ for me."*
- **LeetCode & Coding**:
  - Look at a problem on your screen and say: *"Girisha, look at this LeetCode question on my screen and explain the optimal approach."*
- **Laptop Control**:
  - *"Girisha, open WhatsApp chat Guru Prasad."*
  - *"Girisha, open Notepad and write a 10-minute public speaking plan."*
  - *"Girisha, search the web for the latest updates on quantum computing."*

---

## 📁 Repository Structure

```
MyLife/
├── speech_to_speech.py   # Main Speech-to-Speech + Screen Vision + Teaching engine
├── requirements.txt      # Python dependencies list
├── index.html            # Futuristic phone-call Web UI dashboard
├── server.py             # FastAPI backend for Web UI
├── launch_silent.vbs     # VBScript to launch Girisha silently in background
├── stop_girisha.ps1      # PowerShell script to cleanly terminate background instances
├── study_studio/         # Output directory for generated HTML diagrams & plots
├── README.md             # Complete documentation
└── .gitignore            # Git exclusions (API keys, memory DB, caches)
```

---

## 🛡️ License & Credits
Built by **Giridharan** using the **Google Gemini Multimodal Live API**. Feel free to star ⭐ the repository!
