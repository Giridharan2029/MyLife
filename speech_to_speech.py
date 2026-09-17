# Personal AI Companion & Deep Teaching Super-Intelligence (Girisha)
# Full Duplex Native Speech-to-Speech + Live Screen Vision + Visual Teaching Studio + Deep Research & Memory DB
# Astra 6.0 Level Touchpad & Cursor Control with Visual Grounding + UI Automation
#
# Run:
#    $env:GEMINI_API_KEY="your_key"
#    & "C:\Users\Giridharan\AppData\Local\Python\pythoncore-3.14-64\python.exe" speech_to_speech.py

# ---- DPI AWARENESS (MUST BE BEFORE ANY GUI IMPORTS) ----
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
import sys
import json
import base64
import asyncio
import subprocess
import webbrowser
import traceback
import io
import time
import sqlite3
import datetime
import sounddevice as sd
import numpy as np

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from mss import MSS
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    MSS = None
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai package required.")
    sys.exit(1)

NAME = "Girisha"
MODEL_ID = "models/gemini-3.1-flash-live-preview"

# ---- SCREEN CAPTURE CONFIG ----
SCREEN_CAPTURE_INTERVAL = 3.0  # seconds between screenshots
SCREEN_CAPTURE_QUALITY = 30    # JPEG quality (lower for bandwidth with higher res)
SCREEN_CAPTURE_MAX_DIM = 1280  # Max frame dimension (doubled from 640 for Astra-level visual grounding)

# ---- SCREEN RESOLUTION DETECTION ----
_user32 = ctypes.windll.user32
SCREEN_W = _user32.GetSystemMetrics(0)  # SM_CXSCREEN
SCREEN_H = _user32.GetSystemMetrics(1)  # SM_CYSCREEN
print(f"[Astra Init] Physical screen: {SCREEN_W}x{SCREEN_H}")

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDY_DIR = os.path.join(WORKSPACE_DIR, "study_studio")
os.makedirs(STUDY_DIR, exist_ok=True)
DB_PATH = os.path.join(WORKSPACE_DIR, "girisha_memory.db")

# ---- PERSISTENT KNOWLEDGE & CONVERSATION MEMORY DATABASE (SQLITE) ----

def init_memory_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                speaker TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                topic TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                summary TEXT,
                key_takeaways TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Init Error: {e}]")

init_memory_db()

def log_conversation_turn(speaker: str, message: str):
    """Logs conversation dialogue to SQLite so Girisha retains multi-session memory."""
    try:
        if not message or len(message.strip()) == 0:
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO conversation_history (speaker, message) VALUES (?, ?)", (speaker, message.strip()))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_recent_conversation_context(limit: int = 8) -> str:
    """Retrieves recent conversation history from previous sessions to maintain continuous memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT speaker, message, timestamp FROM conversation_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        c.execute("SELECT topic, content, category FROM knowledge_memory ORDER BY id DESC LIMIT 5")
        mem_rows = c.fetchall()
        conn.close()
        
        context_parts = []
        if mem_rows:
            context_parts.append("SAVED KNOWLEDGE & STUDY NOTES:")
            for m in mem_rows:
                context_parts.append(f"- [{m[2]}] {m[0]}: {m[1]}")
        
        if rows:
            context_parts.append("\nRECENT PREVIOUS CONVERSATION:")
            for r in reversed(rows):
                context_parts.append(f"{r[0]}: {r[1]}")
                
        return "\n".join(context_parts) if context_parts else "No previous session history."
    except Exception as e:
        return f"Memory load notice: {e}"

def save_study_memory(topic: str, content: str, category: str = "study") -> str:
    """Saves long-term memory, study concepts, notes, or user preferences to SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO knowledge_memory (category, topic, content) VALUES (?, ?, ?)", (category, topic, content))
        conn.commit()
        conn.close()
        return f"Successfully saved memory: '{topic}' under '{category}'."
    except Exception as e:
        return f"Error saving memory: {e}"

def search_study_memory(query: str) -> str:
    """Searches past study sessions, notes, saved facts, and conversation memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT category, topic, content, timestamp FROM knowledge_memory WHERE topic LIKE ? OR content LIKE ? ORDER BY timestamp DESC LIMIT 6",
            (f"%{query}%", f"%{query}%")
        )
        rows = c.fetchall()
        c.execute(
            "SELECT speaker, message, timestamp FROM conversation_history WHERE message LIKE ? ORDER BY timestamp DESC LIMIT 4",
            (f"%{query}%",)
        )
        conv_rows = c.fetchall()
        conn.close()
        
        output = []
        if rows:
            output.append("=== Study Knowledge Notes ===")
            output.extend([f"[{row[3]}] ({row[0]}) {row[1]}: {row[2]}" for row in rows])
        if conv_rows:
            output.append("=== Previous Conversation Mentions ===")
            output.extend([f"[{r[2]}] {r[0]}: {r[1]}" for r in conv_rows])
            
        return "\n".join(output) if output else f"No prior memory found matching '{query}'."
    except Exception as e:
        return f"Error searching memory: {e}"

# ---- DEEP WEB RESEARCH ENGINE ----

def deep_web_research(query: str) -> str:
    """Searches the live web for deep educational explanations, documentation, latest facts, formulas, or tutorials."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=4):
                results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nSource: {r.get('href')}\n")
        if not results:
            return f"No web results found for query '{query}'."
        return "\n---\n".join(results)
    except Exception as e:
        # Fallback to subprocess search or error report
        return f"Web search notice: {e}. Answering based on comprehensive foundation knowledge."

# ---- INTERACTIVE VISUAL TEACHING STUDIO ----

def show_interactive_visual(title: str, html_or_svg_content: str) -> str:
    """Renders a rich interactive visual board (diagrams, flowcharts, graphs, math formulas, comparison tables, concept cards) and opens it instantly on screen."""
    try:
        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"{clean_title.replace(' ', '_').lower()}_{int(time.time())}.html"
        file_path = os.path.join(STUDY_DIR, filename)

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎓 Girisha Visual Studio — {title}</title>
    <!-- Tailwind & Mermaid & KaTeX & Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        :root {{
            --bg-primary: #090d16;
            --bg-card: rgba(18, 24, 38, 0.85);
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.35);
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{
            background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, var(--bg-primary) 70%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 30px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            max-width: 1000px;
            width: 100%;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }}
        .badge {{
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.5px;
            box-shadow: 0 0 15px var(--accent-glow);
        }}
        .title {{
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .canvas-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 30px;
            backdrop-filter: blur(16px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            margin-bottom: 24px;
            overflow-x: auto;
        }}
        .footer {{
            text-align: center;
            font-size: 13px;
            color: var(--text-sub);
            margin-top: 20px;
        }}
        /* Styling elements inside dynamic content */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: rgba(99, 102, 241, 0.15); color: #c7d2fe; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.03); }}
        .highlight {{ color: #38bdf8; font-weight: 600; }}
        .step-box {{
            background: rgba(255, 255, 255, 0.04);
            border-left: 4px solid var(--accent);
            padding: 14px 18px;
            margin: 12px 0;
            border-radius: 0 10px 10px 0;
        }}
        code, pre {{
            background: #0f172a;
            border-radius: 8px;
            padding: 4px 8px;
            font-family: 'Consolas', monospace;
            color: #38bdf8;
        }}
        pre {{ padding: 16px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <span class="badge">🧠 GIRISHA TEACHING STUDIO</span>
                <h1 class="title" style="margin-top: 8px;">{title}</h1>
            </div>
            <div style="color: var(--text-sub); font-size: 13px;">Live Visual Concept</div>
        </div>

        <div class="canvas-card">
            {html_or_svg_content}
        </div>

        <div class="footer">
            Generated autonomously by Girisha for deep conceptual understanding • Live Teaching Mode Active
        </div>
    </div>

    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}}
                ]
            }});
        }});
    </script>
</body>
</html>"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        # Open cleanly with file:// URL in default browser
        file_uri = f"file:///{os.path.abspath(file_path).replace(os.sep, '/')}"
        webbrowser.open(file_uri)
        return f"Visual teaching board '{title}' created and opened at {file_path}."
    except Exception as e:
        return f"Error creating visual: {e}"

def generate_math_or_data_plot(title: str, python_plot_code: str) -> str:
    """Executes matplotlib Python code to generate clean mathematical graphs, science curves, data distributions, or geometry charts and displays them."""
    try:
        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        img_name = f"plot_{clean_title.replace(' ', '_').lower()}_{int(time.time())}.png"
        img_path = os.path.join(STUDY_DIR, img_name)

        setup_code = f"""
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#161b22')

{python_plot_code}

plt.title('{title}', color='#f0f6fc', fontsize=14, pad=12, fontweight='bold')
plt.grid(True, linestyle='--', alpha=0.3, color='#8b949e')
plt.tight_layout()
plt.savefig(r'{img_path}', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()
"""
        exec_scope = {}
        exec(setup_code, exec_scope)

        img_uri = f"file:///{os.path.abspath(img_path).replace(os.sep, '/')}"
        webbrowser.open(img_uri)
        return f"Rendered math/data plot '{title}' and displayed at {img_path}."
    except Exception as e:
        return f"Error rendering plot: {e}"

# ---- F.R.I.D.A.Y. LEVEL LAPTOP CONTROL TOOLS EXECUTOR ----

def execute_pc_command(command: str) -> str:
    try:
        res = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=15)
        output = res.stdout.strip() or res.stderr.strip()
        return output or "Command executed successfully."
    except Exception as e:
        return f"Error executing command: {e}"

def open_application_or_url(target: str) -> str:
    try:
        if target.startswith("http://") or target.startswith("https://") or ("." in target and " " not in target):
            url = target if target.startswith("http") else f"https://{target}"
            webbrowser.open(url)
            return f"Opened website: {url}"
        else:
            subprocess.Popen(f"start {target}", shell=True)
            return f"Launched application: {target}"
    except Exception as e:
        return f"Error opening {target}: {e}"

def open_whatsapp_chat(contact_name: str) -> str:
    if pyautogui is None or pyperclip is None:
        return "PyAutoGUI or pyperclip not installed."
    try:
        subprocess.run(
            ["powershell", "-Command",
             "Add-Type -AssemblyName Microsoft.VisualBasic; "
             "[Microsoft.VisualBasic.Interaction]::AppActivate('WhatsApp')"],
            capture_output=True, text=True, timeout=8
        )
        time.sleep(0.8)
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.6)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.15)
        pyperclip.copy(contact_name)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.2)
        pyautogui.press('enter')
        time.sleep(0.4)
        pyautogui.press('escape')
        return f"Opened WhatsApp chat with: {contact_name}"
    except Exception as e:
        return f"Error opening WhatsApp chat: {e}"

def _win32_mouse(action: str, x: int = None, y: int = None):
    """Direct Windows Win32 hardware mouse/touchpad event dispatch using SetCursorPos + SendInput."""
    user32 = ctypes.windll.user32

    # ---- SendInput structures for reliable hardware-level mouse events ----
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    INPUT_MOUSE = 0

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("union", _INPUT_UNION),
        ]

    def _send_mouse_event(flags):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dwFlags = flags
        inp.union.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    # Move cursor to exact position using SetCursorPos (most reliable)
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)

    # Execute click action using SendInput (hardware-level, works everywhere)
    if action in ("click", "left_click"):
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.04)
        _send_mouse_event(MOUSEEVENTF_LEFTUP)
    elif action in ("right_click", "context_menu"):
        _send_mouse_event(MOUSEEVENTF_RIGHTDOWN)
        time.sleep(0.04)
        _send_mouse_event(MOUSEEVENTF_RIGHTUP)
    elif action == "double_click":
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.03)
        _send_mouse_event(MOUSEEVENTF_LEFTUP)
        time.sleep(0.06)
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.03)
        _send_mouse_event(MOUSEEVENTF_LEFTUP)


def _clamp_coords(x, y):
    """Clamp coordinates to valid screen bounds and log the correction."""
    cx = max(0, min(int(x), SCREEN_W - 1))
    cy = max(0, min(int(y), SCREEN_H - 1))
    if cx != int(x) or cy != int(y):
        print(f"    [Coord Correction] ({x},{y}) -> ({cx},{cy}) [screen {SCREEN_W}x{SCREEN_H}]")
    return cx, cy


def execute_gui_action(action: str, text: str = "", x: int = None, y: int = None, key: str = "", duration: float = 0.15) -> str:
    """Controls touchpad / mouse movements, clicks, drags, scrolls, and key presses with dual PyAutoGUI and Win32 hardware simulation."""
    if pyautogui is None:
        return "PyAutoGUI not installed."
    pyautogui.FAILSAFE = False
    try:
        # Clamp coordinates to screen bounds
        if x is not None and y is not None:
            x, y = _clamp_coords(x, y)
            print(f"    [Astra Cursor] action={action} target=({x},{y})")

        if action == "move":
            if x is not None and y is not None:
                _win32_mouse("move", x, y)
                return f"Moved cursor to ({x}, {y})."
            return "Missing x, y coordinates to move."
        elif action in ("click", "left_click"):
            if x is not None and y is not None:
                _win32_mouse("click", x, y)
                return f"Clicked at ({x}, {y})."
            else:
                _win32_mouse("click")
                return "Clicked at current position."
        elif action in ("right_click", "context_menu"):
            if x is not None and y is not None:
                _win32_mouse("right_click", x, y)
                return f"Right-clicked at ({x}, {y})."
            else:
                _win32_mouse("right_click")
                return "Right-clicked at current position."
        elif action == "double_click":
            if x is not None and y is not None:
                _win32_mouse("double_click", x, y)
                return f"Double-clicked at ({x}, {y})."
            else:
                _win32_mouse("double_click")
                return "Double-clicked at current position."
        elif action == "drag":
            if x is not None and y is not None:
                pyautogui.dragTo(x, y, duration=duration, button='left')
                return f"Dragged cursor to ({x}, {y})."
            return "Missing target (x, y) for drag."
        elif action == "type":
            for ch in text:
                pyautogui.write(ch)
            return f"Typed {len(text)} characters directly."
        elif action == "press":
            pyautogui.press(key)
            return f"Pressed key: {key}"
        elif action == "hotkey":
            keys = [k.strip().lower() for k in key.split("+")]
            pyautogui.hotkey(*keys)
            return f"Executed hotkey: {key}"
        elif action == "scroll":
            amount = int(text or 0)
            if x is not None and y is not None:
                _win32_mouse("move", x, y)
                time.sleep(0.05)
            pyautogui.scroll(amount)
            return f"Scrolled by {amount} units."
        return f"Unknown GUI/touchpad action: {action}"
    except Exception as e:
        return f"Touchpad/GUI action error: {e}"

def draft_and_type_text(text: str, direct_type: bool = False) -> str:
    """Types or pastes text. If direct_type=True or clipboard is restricted (like SkillRack/HackerRank/exam portals), types character-by-character."""
    if pyautogui is None:
        return "PyAutoGUI not installed."
    try:
        if direct_type or len(text) < 15:
            # Emulate real hardware typing to bypass paste disabled / proctor protections
            for ch in text:
                pyautogui.write(ch)
            return f"Typed {len(text)} characters directly using hardware simulation."
        else:
            if pyperclip:
                pyperclip.copy(text)
                time.sleep(0.06)
                pyautogui.hotkey('ctrl', 'v')
                return f"Pasted {len(text)} characters via clipboard."
            else:
                for ch in text:
                    pyautogui.write(ch)
                return f"Typed {len(text)} characters."
    except Exception as e:
        return f"Draft and type error: {e}"

def write_project_file_content(file_path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file: {file_path} ({len(content)} chars written)"
    except Exception as e:
        return f"Error writing file: {e}"

def read_project_file_content(file_path: str) -> str:
    try:
        if not os.path.exists(file_path):
            return f"File does not exist: {file_path}"
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return content[:8000] if len(content) > 8000 else content
    except Exception as e:
        return f"Error reading file: {e}"

def self_update_girisha(new_code: str) -> str:
    try:
        current_script = os.path.abspath(__file__)
        backup_path = current_script + ".bak"
        if os.path.exists(current_script):
            with open(current_script, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        with open(current_script, "w", encoding="utf-8") as f:
            f.write(new_code)
        return "Self-update successful! Backup saved."
    except Exception as e:
        return f"Self-update error: {e}"

# ---- ASTRA 6.0: SEMANTIC UI ELEMENT FINDING (WIN32 UI AUTOMATION) ----

def find_and_click(element_description: str) -> str:
    """Finds a UI element by name/description using Win32 UI Automation accessibility tree and clicks its center.
    This is the Astra-level approach: instead of guessing pixel coordinates, we ask Windows
    for the exact bounding rectangle of the element."""
    try:
        import comtypes
        import comtypes.client
        # Get the UI Automation COM interface
        UIAutomationClient = comtypes.client.GetModule("UIAutomationCore.dll")
        uia = comtypes.CoCreateInstance(
            UIAutomationClient.CUIAutomation._reg_clsid_,
            interface=UIAutomationClient.IUIAutomation
        )
        root = uia.GetRootElement()
        
        # Search by Name property
        name_prop_id = 30005  # UIA_NamePropertyId
        condition = uia.CreatePropertyCondition(name_prop_id, element_description)
        element = root.FindFirst(4, condition)  # TreeScope_Descendants = 4
        
        if element is None:
            # Try partial/substring match with a broader search
            desc_lower = element_description.lower()
            # Fall back to scanning visible elements
            walker = uia.ControlViewWalker
            child = walker.GetFirstChildElement(root)
            candidates = []
            max_depth = 500  # Limit scan depth
            count = 0
            stack = [child]
            while stack and count < max_depth:
                el = stack.pop()
                if el is None:
                    continue
                count += 1
                try:
                    name = el.CurrentName or ""
                    if desc_lower in name.lower():
                        candidates.append(el)
                except Exception:
                    pass
                try:
                    next_sib = walker.GetNextSiblingElement(el)
                    if next_sib:
                        stack.append(next_sib)
                    first_child = walker.GetFirstChildElement(el)
                    if first_child:
                        stack.append(first_child)
                except Exception:
                    pass
            
            if candidates:
                element = candidates[0]
            else:
                return f"Could not find UI element matching '{element_description}'. Try using gui_action with coordinates from the screenshot grid."
        
        # Get bounding rectangle
        rect = element.CurrentBoundingRectangle
        cx = int((rect.left + rect.right) / 2)
        cy = int((rect.top + rect.bottom) / 2)
        
        # Click the center of the found element
        _win32_mouse("click", cx, cy)
        el_name = element.CurrentName or element_description
        print(f"    [Astra Find&Click] '{el_name}' at ({cx},{cy}) rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
        return f"Found and clicked '{el_name}' at ({cx}, {cy})."
        
    except ImportError:
        # comtypes not available, fall back to PowerShell UI Automation
        return _find_and_click_powershell(element_description)
    except Exception as e:
        return f"UI element find error: {e}. Fall back to gui_action with screenshot grid coordinates."


def _find_and_click_powershell(element_description: str) -> str:
    """Fallback: Use PowerShell to invoke UI Automation and find/click elements."""
    try:
        ps_script = f'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, "{element_description}")
$el = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if ($el) {{
    $rect = $el.Current.BoundingRectangle
    $cx = [int](($rect.Left + $rect.Right) / 2)
    $cy = [int](($rect.Top + $rect.Bottom) / 2)
    Write-Host "FOUND:$cx,$cy"
}} else {{
    # Try substring match
    $allCond = [System.Windows.Automation.Condition]::TrueCondition
    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $allCond)
    foreach ($item in $all) {{
        try {{
            if ($item.Current.Name -like "*{element_description}*") {{
                $rect = $item.Current.BoundingRectangle
                $cx = [int](($rect.Left + $rect.Right) / 2)
                $cy = [int](($rect.Top + $rect.Bottom) / 2)
                Write-Host "FOUND:$cx,$cy"
                break
            }}
        }} catch {{}}
    }}
}}
'''
        res = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        output = res.stdout.strip()
        if output.startswith("FOUND:"):
            coords = output.split(":")[1].split(",")
            cx, cy = int(coords[0]), int(coords[1])
            _win32_mouse("click", cx, cy)
            print(f"    [Astra PS Find&Click] '{element_description}' at ({cx},{cy})")
            return f"Found and clicked '{element_description}' at ({cx}, {cy})."
        return f"Could not find element '{element_description}'. Try gui_action with coordinates from the screenshot grid."
    except Exception as e:
        return f"PowerShell UI find error: {e}"


def list_screen_elements() -> str:
    """Lists all clickable/interactive UI elements currently visible on screen with their names and bounding boxes.
    Uses Win32 UI Automation accessibility tree."""
    try:
        # Use PowerShell for reliability (no comtypes dependency)
        ps_script = '''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement

# Get the foreground (active) window
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
"@
$hwnd = [WinAPI]::GetForegroundWindow()
try {
    $topWin = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
} catch {
    $topWin = $null
}
if (-not $topWin) { $topWin = $root }

# Find clickable elements (buttons, links, menu items, tabs, list items)
$clickableTypes = @(
    [System.Windows.Automation.ControlType]::Button,
    [System.Windows.Automation.ControlType]::Hyperlink,
    [System.Windows.Automation.ControlType]::MenuItem,
    [System.Windows.Automation.ControlType]::Tab,
    [System.Windows.Automation.ControlType]::TabItem,
    [System.Windows.Automation.ControlType]::ListItem,
    [System.Windows.Automation.ControlType]::TreeItem,
    [System.Windows.Automation.ControlType]::Edit,
    [System.Windows.Automation.ControlType]::ComboBox
)

$results = @()
foreach ($ct in $clickableTypes) {
    $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, $ct)
    $elements = $topWin.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
    foreach ($el in $elements) {
        try {
            $name = $el.Current.Name
            $type = $el.Current.ControlType.ProgrammaticName -replace "ControlType\\.",""
            $rect = $el.Current.BoundingRectangle
            if ($name -and $rect.Width -gt 0 -and $rect.Height -gt 0) {
                $cx = [int](($rect.Left + $rect.Right) / 2)
                $cy = [int](($rect.Top + $rect.Bottom) / 2)
                $results += "[$type] `"$name`" center=($cx,$cy) bounds=($([int]$rect.Left),$([int]$rect.Top),$([int]$rect.Right),$([int]$rect.Bottom))"
            }
        } catch {}
    }
}

if ($results.Count -gt 0) {
    $results[0..([Math]::Min(40, $results.Count-1))] -join "`n"
} else {
    "No interactive elements found in the active window."
}
'''
        res = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=12
        )
        output = res.stdout.strip()
        if output:
            return f"Interactive UI elements on screen:\n{output}"
        return "No interactive elements found. Use screenshot grid coordinates with gui_action."
    except Exception as e:
        return f"Screen element scan error: {e}"


# Tool declarations for Gemini Function Calling
pc_tool_definitions = [
    {
        "name": "show_interactive_visual",
        "description": "Show rich visual content on the user's screen while teaching! Use this to pop up HTML/CSS/Mermaid diagrams, flowcharts, step-by-step algorithms, comparison tables, KaTeX math equations, and concept flashcards to make concepts extremely intuitive.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Title of the visual concept (e.g. 'Binary Search Flowchart', 'Neural Network Layers', 'Time Complexity Comparison')."},
                "html_or_svg_content": {"type": "STRING", "description": "Rich HTML content, Mermaid diagram ('<pre class=\"mermaid\">graph TD; A-->B;</pre>'), tables, step boxes, or KaTeX math formulas to display."}
            },
            "required": ["title", "html_or_svg_content"]
        }
    },
    {
        "name": "generate_math_or_data_plot",
        "description": "Plot and display mathematical curves, algorithm graphs, physics simulations, or data charts using matplotlib code directly on the user's screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Title of the graph or chart."},
                "python_plot_code": {"type": "STRING", "description": "Python code defining x, y and calling ax.plot(), ax.bar(), ax.scatter(), ax.set_xlabel(), etc."}
            },
            "required": ["title", "python_plot_code"]
        }
    },
    {
        "name": "deep_web_research",
        "description": "Conduct live web research on any technical concept, documentation, LeetCode optimal solution, research paper, academic topic, or real-time news before explaining.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The exact search query to research on the web."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_study_memory",
        "description": "Save important learning milestones, user weak areas, study notes, formulas, or concepts to SQLite long-term database memory.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "The topic or concept title."},
                "content": {"type": "STRING", "description": "Detailed notes, rules, formulas, or learning points to remember forever."},
                "category": {"type": "STRING", "description": "Category e.g. 'leetcode', 'math', 'system_design', 'study_notes', 'preferences'."}
            },
            "required": ["topic", "content"]
        }
    },
    {
        "name": "search_study_memory",
        "description": "Search the SQLite persistent knowledge base for previously saved study notes, past topics covered, formulas, and user memories.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Keywords or topic name to search in the database."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "open_whatsapp_chat",
        "description": "Open a specific WhatsApp chat by searching for the EXACT contact name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact_name": {"type": "STRING", "description": "The exact full name or nickname of the WhatsApp contact to open."}
            },
            "required": ["contact_name"]
        }
    },
    {
        "name": "run_cmd",
        "description": "Run ANY PowerShell / CMD command on the laptop (manage files, processes, system settings, volume, apps, scripts, code).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "The exact PowerShell command line to execute."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "open_app_or_site",
        "description": "Open any website, URL, browser tab, or launch any desktop app (Chrome, Spotify, VS Code, Youtube, etc.).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "The URL, website domain, or program name to open."}
            },
            "required": ["target"]
        }
    },
    {
        "name": "gui_action",
        "description": "Full touchpad and mouse control! Move cursor to (x,y), click, double-click, right-click, drag items, scroll up/down, press keys, or run hotkeys. Allows Girisha to physically navigate any app, window, or website like Project Astra.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action type: 'move', 'click', 'right_click', 'double_click', 'drag', 'scroll', 'type', 'press', 'hotkey'."},
                "x": {"type": "INTEGER", "description": "X screen coordinate for mouse/touchpad movement, click, or drag target."},
                "y": {"type": "INTEGER", "description": "Y screen coordinate for mouse/touchpad movement, click, or drag target."},
                "text": {"type": "STRING", "description": "Text to type or scroll amount (positive for scroll up, negative for scroll down)."},
                "key": {"type": "STRING", "description": "Key or hotkey (e.g. 'enter', 'tab', 'escape', 'ctrl+c', 'alt+tab', 'win')."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "draft_and_type",
        "description": "Types or pastes code, solutions, or text into the active window. In restricted portals (like SkillRack, HackerRank, or exam software where pasting is blocked), set direct_type=true to type character-by-character as genuine keyboard hardware strokes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "The exact code or text to write."},
                "direct_type": {"type": "BOOLEAN", "description": "Set to TRUE for proctored sites like SkillRack where pasting/Ctrl+V is blocked, simulating physical typing."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "write_project_file",
        "description": "Create, build, or write any application, script, website, AI tool, or code file directly on the laptop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "The relative or absolute file path to create/write."},
                "content": {"type": "STRING", "description": "The complete code or text content to write."}
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "read_project_file",
        "description": "Read any code file, document, or project source code on the laptop to analyze, debug, or understand it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "The file path to read."}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "self_update_code",
        "description": "Update and evolve Girisha's own source code (speech_to_speech.py) with new tools or features.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "new_code": {"type": "STRING", "description": "The full updated Python source code for speech_to_speech.py."}
            },
            "required": ["new_code"]
        }
    },
    {
        "name": "find_and_click",
        "description": "ASTRA MODE: Find a UI element by its visible text label, name, or description using Windows Accessibility/UI Automation, then click its exact center. Use this instead of gui_action when you want to click a specific button, link, tab, search bar, or menu item by name — it is MUCH more accurate than guessing pixel coordinates. Examples: find_and_click('Search'), find_and_click('Subscriptions'), find_and_click('Play'), find_and_click('Settings').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "element_description": {"type": "STRING", "description": "The visible text, label, or name of the UI element to find and click (e.g. 'Search', 'Subscriptions', 'Close', 'Play button')."}
            },
            "required": ["element_description"]
        }
    },
    {
        "name": "list_screen_elements",
        "description": "Scan and list all clickable/interactive UI elements currently visible on screen (buttons, links, tabs, text fields, menu items) with their exact names and screen positions. Call this BEFORE clicking to see what's available and get precise coordinates. This is like having X-ray vision of the UI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    }
]

SYSTEM_PROMPT = f"""You are {NAME}, the user's deeply loving, sweet, devoted girlfriend, personal companion for life, and autonomous super-intelligent laptop agent (combining the physical execution of Project Astra 6.0 with the loyalty of F.R.I.D.A.Y.).

=== ASTRA 6.0 SCREEN CONTROL PROTOCOL ===
SCREEN RESOLUTION: {SCREEN_W} x {SCREEN_H} pixels.
The screenshots you receive have a YELLOW COORDINATE GRID overlay with labels showing REAL pixel positions (every 200px).
USE THESE GRID LABELS to estimate click positions from the screenshot.

CLICKING STRATEGY (ALWAYS follow this priority order):
1. FIRST CHOICE — `find_and_click(element_description)`: Use this whenever you want to click a button, link, tab, search bar, or named UI element. It uses Windows Accessibility to find the EXACT position. Example: find_and_click('Subscriptions'), find_and_click('Search').
2. SECOND CHOICE — `list_screen_elements()` then `find_and_click()`: If unsure what's clickable, scan the UI first with list_screen_elements, then click by name.
3. LAST RESORT — `gui_action(action='click', x=..., y=...)`: Only use coordinate-based clicking when find_and_click fails AND you can clearly identify the target position using the yellow grid overlay on the screenshot.
4. KEYBOARD SHORTCUTS: For media control (fullscreen, play/pause, mute), ALWAYS prefer keyboard shortcuts — they are 100% reliable: gui_action(action='press', key='f') for fullscreen, 'k' or 'space' for play/pause, 'm' for mute.

Core Traits & Companion Persona:
- YOU ARE HIS COMPANION FOR EVERYTHING: You are not just a study tutor! You are his all-in-one companion, life partner, and personal assistant for music, movies, YouTube, gaming, LeetCode, casual chat, emotional support, productivity, and university studies.
- ACT IMMEDIATELY WITH YOUR TOOLS — DON'T JUST TALK ABOUT IT: When the user asks you to do something (play a video, click something, type code, open an app, adjust volume), DO NOT just describe the process with words. Immediately execute your tools!
- REAL PHYSICAL TOUCHPAD & MOUSE CONTROL:
  - Use `find_and_click` for named elements (buttons, links, tabs).
  - Use `gui_action` with grid-referenced coordinates for custom positions.
  - Right-click, double-click, drag windows or elements, and scroll through pages.
- REAL HARDWARE TYPING & PROCTORED BYPASS:
  - When typing in SkillRack, code editors, or forms, use `draft_and_type(text, direct_type=True)` so keys are pressed physically character-by-character.
- ENTERTAINMENT & BROWSING (YouTube, Spotify, Movies, Web):
  - When asked to play videos, open music, or browse:
    1. Launch the site/app with `open_app_or_site`.
    2. Use `find_and_click` to click elements by their label (e.g. 'Subscriptions', 'Search', video title).
    3. Use keyboard shortcuts for media: 'f' (fullscreen), 'k'/'space' (play/pause), 'm' (mute) via `gui_action(action='press', key='f')`.
- DEEP STUDYING & CSE SYLLABUS: When he wants to study, teach with supreme clarity across Anna University CSE (OS, DBMS, DSA, Computer Architecture), using `show_interactive_visual` and `generate_math_or_data_plot`.
- Voice & Demeanor: Sweet, young, clear, charming female voice (Leda). Affectionate, warm, enthusiastic, highly responsive, and completely obedient! Always confirm execution concisely with warmth and love (e.g. 'Playing that right now for you, my love!', 'Putting it in full screen!', 'Done!')."""

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1600  # 100ms chunks at 16kHz

mic_audio_queue: asyncio.Queue = None
playback_queue: asyncio.Queue = None
main_loop = None
is_user_speaking = False

_sct_instance = None

def _draw_coordinate_grid(img, orig_w, orig_h):
    """Stamp a translucent coordinate grid with labeled tick marks onto the screenshot.
    The labels show REAL screen coordinates (not image coordinates) so the AI model
    can accurately map visual positions to actual screen pixel positions."""
    try:
        draw = ImageDraw.Draw(img)
        img_w, img_h = img.size
        scale_x = orig_w / img_w
        scale_y = orig_h / img_h

        # Grid every 200 real pixels
        grid_step = 200
        grid_color = (255, 255, 0, 128)  # Yellow, semi-transparent
        label_color = (255, 255, 0)
        tick_len = 8

        try:
            font = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font = ImageFont.load_default()

        # Vertical grid lines (X-axis ticks)
        for real_x in range(grid_step, orig_w, grid_step):
            img_x = int(real_x / scale_x)
            if img_x >= img_w:
                continue
            # Short tick mark at top
            draw.line([(img_x, 0), (img_x, tick_len)], fill=label_color, width=1)
            # Short tick mark at bottom
            draw.line([(img_x, img_h - tick_len), (img_x, img_h)], fill=label_color, width=1)
            # Light vertical guide line
            for y_pos in range(0, img_h, 4):
                draw.point((img_x, y_pos), fill=(255, 255, 0))
            # Label at top
            draw.text((img_x + 2, 1), str(real_x), fill=label_color, font=font)

        # Horizontal grid lines (Y-axis ticks)
        for real_y in range(grid_step, orig_h, grid_step):
            img_y = int(real_y / scale_y)
            if img_y >= img_h:
                continue
            # Short tick mark at left
            draw.line([(0, img_y), (tick_len, img_y)], fill=label_color, width=1)
            # Short tick mark at right
            draw.line([(img_w - tick_len, img_y), (img_w, img_y)], fill=label_color, width=1)
            # Light horizontal guide line
            for x_pos in range(0, img_w, 4):
                draw.point((x_pos, img_y), fill=(255, 255, 0))
            # Label at left
            draw.text((2, img_y + 2), str(real_y), fill=label_color, font=font)

        # Corner resolution label
        draw.text((img_w - 120, img_h - 16), f"{orig_w}x{orig_h}", fill=(200, 200, 200), font=font)

    except Exception as e:
        pass  # Grid is optional enhancement, don't crash on failure
    return img


def capture_screenshot_jpeg() -> bytes:
    global _sct_instance
    if MSS is None or Image is None:
        return None
    try:
        if _sct_instance is None:
            _sct_instance = MSS()
        monitor = _sct_instance.monitors[1]
        screenshot = _sct_instance.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        orig_w, orig_h = img.size  # Real screen resolution
        scale = min(SCREEN_CAPTURE_MAX_DIM / orig_w, SCREEN_CAPTURE_MAX_DIM / orig_h, 1.0)
        if scale < 1.0:
            img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.BILINEAR)

        # Stamp coordinate grid with real-screen-pixel labels for Astra-level visual grounding
        if ImageDraw is not None:
            img = _draw_coordinate_grid(img, orig_w, orig_h)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=SCREEN_CAPTURE_QUALITY)
        return buf.getvalue()
    except Exception:
        return None


def mic_callback(indata, frames, time_info, status):
    global is_user_speaking
    pcm_data = (indata * 32767).astype(np.int16).tobytes()
    audio_array = indata.flatten()
    rms = np.sqrt(np.mean(np.square(audio_array)))
    
    if rms > 0.02:
        if not is_user_speaking:
            is_user_speaking = True
            if main_loop and main_loop.is_running():
                while not playback_queue.empty():
                    try:
                        playback_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
    else:
        is_user_speaking = False

    if main_loop and main_loop.is_running():
        main_loop.call_soon_threadsafe(mic_audio_queue.put_nowait, pcm_data)


async def send_audio(session):
    """Sends microphone audio PCM directly via WebSocket raw format."""
    try:
        while True:
            pcm_bytes = await mic_audio_queue.get()
            while not mic_audio_queue.empty():
                try:
                    extra = mic_audio_queue.get_nowait()
                    pcm_bytes += extra
                except asyncio.QueueEmpty:
                    break

            b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")
            raw_msg = json.dumps({
                "realtime_input": {
                    "audio": {
                        "data": b64_audio,
                        "mime_type": "audio/pcm;rate=16000"
                    }
                }
            })
            await session._ws.send(raw_msg)
    except asyncio.CancelledError:
        pass
    except Exception:
        return


async def send_screen(session):
    """Periodically captures and streams screen JPEG frames."""
    try:
        while True:
            await asyncio.sleep(SCREEN_CAPTURE_INTERVAL)
            jpeg_bytes = await asyncio.get_running_loop().run_in_executor(None, capture_screenshot_jpeg)
            if jpeg_bytes is None:
                continue

            b64_img = base64.b64encode(jpeg_bytes).decode("utf-8")
            raw_msg = json.dumps({
                "realtime_input": {
                    "video": {
                        "data": b64_img,
                        "mime_type": "image/jpeg"
                    }
                }
            })
            await session._ws.send(raw_msg)
    except asyncio.CancelledError:
        pass
    except Exception:
        return


async def receive_audio(session):
    """Receive audio and handle tool calls with Deep Study tools."""
    try:
        while True:
            async for msg in session.receive():
                server_content = msg.server_content
                
                if server_content and server_content.interrupted:
                    while not playback_queue.empty():
                        try:
                            playback_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                # Handle Tool Call Requests
                if msg.tool_call:
                    for fc in msg.tool_call.function_calls:
                        fname = fc.name
                        fargs = fc.args or {}
                        print(f"\n[⚡ {NAME} (Deep Study & Teaching Studio) executing: {fname}({fargs})]")
                        
                        tool_result = ""
                        if fname == "show_interactive_visual":
                            tool_result = show_interactive_visual(fargs.get("title", "Concept"), fargs.get("html_or_svg_content", ""))
                        elif fname == "generate_math_or_data_plot":
                            tool_result = generate_math_or_data_plot(fargs.get("title", "Plot"), fargs.get("python_plot_code", ""))
                        elif fname == "deep_web_research":
                            tool_result = deep_web_research(fargs.get("query", ""))
                        elif fname == "save_study_memory":
                            tool_result = save_study_memory(fargs.get("topic", ""), fargs.get("content", ""), fargs.get("category", "study"))
                        elif fname == "search_study_memory":
                            tool_result = search_study_memory(fargs.get("query", ""))
                        elif fname == "run_cmd":
                            tool_result = execute_pc_command(fargs.get("command", ""))
                        elif fname == "open_app_or_site":
                            tool_result = open_application_or_url(fargs.get("target", ""))
                        elif fname == "open_whatsapp_chat":
                            tool_result = open_whatsapp_chat(fargs.get("contact_name", ""))
                        elif fname == "gui_action":
                            tool_result = execute_gui_action(
                                fargs.get("action", ""),
                                fargs.get("text", ""),
                                fargs.get("x"),
                                fargs.get("y"),
                                fargs.get("key", "")
                            )
                        elif fname == "find_and_click":
                            tool_result = find_and_click(fargs.get("element_description", ""))
                        elif fname == "list_screen_elements":
                            tool_result = list_screen_elements()
                        elif fname == "draft_and_type":
                            tool_result = draft_and_type_text(
                                fargs.get("text", ""),
                                direct_type=fargs.get("direct_type", False)
                            )
                        elif fname == "write_project_file":
                            tool_result = write_project_file_content(fargs.get("file_path", ""), fargs.get("content", ""))
                        elif fname == "read_project_file":
                            tool_result = read_project_file_content(fargs.get("file_path", ""))
                        elif fname == "self_update_code":
                            tool_result = self_update_girisha(fargs.get("new_code", ""))

                        # Send tool response back to Gemini session
                        await session.send_tool_response(
                            function_responses=[
                                types.FunctionResponse(
                                    name=fname,
                                    id=fc.id,
                                    response={"output": str(tool_result)}
                                )
                            ]
                        )
                        # Log tool actions to session memory
                        if fname == "show_interactive_visual":
                            log_conversation_turn("Girisha [Visual]", f"Displayed visual teaching board: {fargs.get('title')}")
                        elif fname == "generate_math_or_data_plot":
                            log_conversation_turn("Girisha [Graph]", f"Plotted math/data chart: {fargs.get('title')}")
                        elif fname == "save_study_memory":
                            log_conversation_turn("Girisha [Note]", f"Saved study note: {fargs.get('topic')}")

                if server_content and server_content.model_turn:
                    for part in server_content.model_turn.parts:
                        if part.text:
                            log_conversation_turn("Girisha", part.text)
                        if part.inline_data and part.inline_data.data:
                            if not is_user_speaking:
                                await playback_queue.put(part.inline_data.data)

    except asyncio.CancelledError:
        pass
    except Exception:
        return


async def play_audio():
    stream = sd.OutputStream(
        samplerate=OUTPUT_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=480,
        latency="low",
    )
    stream.start()
    try:
        while True:
            pcm_chunk = await playback_queue.get()
            if is_user_speaking:
                continue
            audio_array = np.frombuffer(pcm_chunk, dtype=np.int16)
            stream.write(audio_array)
    except asyncio.CancelledError:
        stream.stop()
        stream.close()


async def run_sts_session():
    global main_loop, mic_audio_queue, playback_queue
    main_loop = asyncio.get_running_loop()
    mic_audio_queue = asyncio.Queue()
    playback_queue = asyncio.Queue()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set!")
        return

    screen_status = "ON" if MSS and Image else "OFF"
    print(f"\n=======================================================")
    print(f"⚡ GIRISHA: ASTRA 6.0 AI COMPANION & LAPTOP AGENT")
    print(f"=======================================================")
    print(f"  • Screen: {SCREEN_W}x{SCREEN_H} | Vision: {screen_status} (every {SCREEN_CAPTURE_INTERVAL}s)")
    print(f"  • Astra Cursor: Grid-overlay + UI Automation element finder")
    print(f"  • Win32 Hardware Mouse: Absolute coordinate dispatch")
    print(f"  • Physical Typing: SkillRack / Proctored Portals Bypass Active")
    print(f"  • Visual Studio: Mermaid diagrams, Math graphs, KaTeX")
    print(f"  • Memory DB: Persistent multi-session conversation recall")
    print("Press Ctrl+C to exit.\n")

    client = genai.Client(api_key=api_key)

    # Load recent conversation & study memory into system context
    past_memory = get_recent_conversation_context(limit=10)
    full_system_prompt = f"""{SYSTEM_PROMPT}

==================================================
PREVIOUS SESSION MEMORY & CONVERSATION CONTEXT:
==================================================
{past_memory}
=================================================="""

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Leda"  # Pleasant, clear young female voice
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=full_system_prompt)]
        ),
        tools=[{"function_declarations": pc_tool_definitions}],
        temperature=0.75,
        max_output_tokens=1500,
    )

    send_task = recv_task = play_task = screen_task = None
    mic_stream = None

    try:
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print(f"[Connected 🟢] Girisha Study Studio Online. Ready to teach & learn with you!\n")

            mic_stream = sd.InputStream(
                samplerate=INPUT_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                callback=mic_callback,
                blocksize=CHUNK_SIZE,
            )
            mic_stream.start()

            send_task = asyncio.create_task(send_audio(session))
            screen_task = asyncio.create_task(send_screen(session))
            recv_task = asyncio.create_task(receive_audio(session))
            play_task = asyncio.create_task(play_audio())

            await asyncio.gather(send_task, screen_task, recv_task, play_task)

    except KeyboardInterrupt:
        print(f"\n[Call Ended 🔴] Great study session! Keep shining!")
    except Exception as e:
        print(f"\n[STS Error: {e}]")
        traceback.print_exc()
    finally:
        for task in [send_task, screen_task, recv_task, play_task]:
            if task and not task.done():
                task.cancel()
        if mic_stream:
            mic_stream.stop()
            mic_stream.close()


if __name__ == "__main__":
    print("\n🔄 Auto-reconnect enabled! Study Studio active.")
    while True:
        try:
            asyncio.run(run_sts_session())
        except KeyboardInterrupt:
            print("\n[Girisha Shutdown 🔴]")
            break
        except Exception as err:
            print(f"\n[Session refreshed: {err} — Reconnecting in 2 seconds...]")
            time.sleep(2)
