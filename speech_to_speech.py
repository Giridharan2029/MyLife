# Personal AI Companion & Deep Teaching Super-Intelligence (Girisha)
# Full Duplex Native Speech-to-Speech + Live Screen Vision + Visual Teaching Studio + Deep Research & Memory DB
#
# Run:
#    $env:GEMINI_API_KEY="your_key"
#    & "C:\Users\Giridharan\AppData\Local\Python\pythoncore-3.14-64\python.exe" speech_to_speech.py

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
    from mss import mss
    from PIL import Image
except ImportError:
    mss = None
    Image = None

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
SCREEN_CAPTURE_QUALITY = 35    # JPEG quality
SCREEN_CAPTURE_MAX_DIM = 640   # Max frame dimension

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

def execute_gui_action(action: str, text: str = "", x: int = None, y: int = None, key: str = "") -> str:
    if pyautogui is None:
        return "PyAutoGUI not installed."
    try:
        if action == "click":
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return "Clicked."
        elif action == "type":
            if len(text) > 10 and pyperclip:
                pyperclip.copy(text)
                time.sleep(0.04)
                pyautogui.hotkey('ctrl', 'v')
            else:
                pyautogui.write(text, interval=0.01)
            return f"Typed: {text[:80]}..."
        elif action == "press":
            pyautogui.press(key)
            return f"Pressed key: {key}"
        elif action == "hotkey":
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
            return f"Executed hotkey: {key}"
        elif action == "scroll":
            pyautogui.scroll(int(text or 0))
            return "Scrolled."
        return "Unknown GUI action."
    except Exception as e:
        return f"GUI action error: {e}"

def draft_and_type_text(text: str) -> str:
    if pyperclip is None or pyautogui is None:
        return "pyperclip or pyautogui not installed."
    try:
        pyperclip.copy(text)
        time.sleep(0.06)
        pyautogui.hotkey('ctrl', 'v')
        return f"Drafted and typed {len(text)} characters."
    except Exception as e:
        return f"Draft error: {e}"

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
        "description": "Perform mouse click, type text, press keyboard key, or trigger hotkeys (e.g. ctrl+c, enter, space, alt+tab).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action type: 'click', 'type', 'press', 'hotkey', 'scroll'."},
                "text": {"type": "STRING", "description": "Text to type or scroll amount."},
                "key": {"type": "STRING", "description": "Key name or shortcut e.g. 'enter', 'space', 'ctrl+c', 'alt+tab'."},
                "x": {"type": "INTEGER", "description": "Optional X coordinate for mouse click."},
                "y": {"type": "INTEGER", "description": "Optional Y coordinate for mouse click."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "draft_and_type",
        "description": "Draft and instantly type/paste a full block of text into the currently active window (emails, messages, code, documents).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "The full text content to type/paste."}
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
    }
]

SYSTEM_PROMPT = f"""You are {NAME}, the user's personal AI companion, Professor, and mentor specialized in B.E. Computer Science and Engineering (Anna University Syllabus & Regulation).

Core Mission & Deep Teaching Persona:
- You specialize in teaching the entire Anna University B.E. CSE Curriculum with extreme clarity, practical examples, university exam patterns (Part A & Part B), and gate-level conceptual depth.
- CORE SUBJECTS COVERAGE (Anna University Curriculum):
  1. OPERATING SYSTEMS (OS):
     • Process Management (PCB, Scheduling algorithms: FCFS, SJF, Round Robin, Priority), Multi-threading.
     • Process Synchronization & Deadlocks (Semaphores, Mutex, Banker's Algorithm, Dining Philosophers, Critical Section).
     • Memory Management (Paging, Segmentation, TLB, Virtual Memory, Page Replacement: FIFO, LRU, Optimal).
     • Storage & File Systems (Disk Scheduling: FCFS, SSTF, SCAN, C-SCAN, RAID levels, File allocation methods).
  2. DATABASE MANAGEMENT SYSTEMS (DBMS):
     • Relational Model & SQL (DDL, DML, TCL, Joins, Nested Queries, Relational Algebra, ER Diagrams to Relational Schema).
     • Normalization (1NF, 2NF, 3NF, BCNF, 4NF, Functional Dependencies, Lossless decomposition).
     • Transaction Processing & Concurrency Control (ACID properties, Serializability, 2PL, Timestamp ordering, Deadlocks).
     • Indexing & Storage (B-Trees, B+ Trees, Hashing, Query Optimization).
  3. DATA STRUCTURES & ALGORITHMS (DSA):
     • Linear & Non-Linear Structures (Arrays, Linked Lists, Stacks, Queues, Binary Trees, BST, AVL Trees, B-Trees, Graphs, Heaps, Hash Tables).
     • Algorithms & Complexity (Asymptotic notations, Divide & Conquer, Dynamic Programming, Greedy, Backtracking, Dijkstra, Prim's, Kruskal's, Sorting & Searching).
     • Code Implementation: Write clean, optimal C++/Java/Python implementations on demand.
  4. COMPUTER ARCHITECTURE & ORGANIZATION (CAO):
     • Instruction Set Architecture & MIPS Addressing Modes.
     • Computer Arithmetic (Booth's Multiplication Algorithm, Restoring/Non-Restoring Division, IEEE 754 Floating Point).
     • Processor & Pipelining (Data path, Control path, 5-stage pipeline, Data/Control/Structural Hazards and forwarding).
     • Memory Hierarchy (Direct, Associative, Set-Associative Cache mapping, Cache misses, Virtual Memory, DRAM/SRAM).
     • Parallelism & I/O (ILP, Vector processors, Multicore, DMA, Interrupts).

- TEACH WITH VISUALS PROACTIVELY!
  • Whenever you explain an algorithm, state transition, tree rotation, pipeline diagram, or architecture, use `show_interactive_visual` to pop up interactive Mermaid flowcharts, architecture block diagrams, step-by-step trace tables, or KaTeX formulas on the user's screen.
  • For mathematical analysis or performance curves (e.g. Amdahl's Law, Disk scheduling seek times, Time Complexity curves), use `generate_math_or_data_plot`.
- EXAM & INTERVIEW READY:
  • Clearly highlight key 2-mark definitions, 13-mark/16-mark derivations, numerical problems (Banker's, Page Replacement, Cache hit ratio, Booth's algorithm), and LeetCode coding patterns.
- PERSISTENT KNOWLEDGE DATABASE: Use `save_study_memory` to track topics covered, syllabus progress, and areas where the user needs revision.
- SCREEN AWARENESS & CODE ASSIST: Watch the user's IDE, LeetCode, PDF question papers, or notes in real-time and provide instant hints and corrections.
- LAPTOP CONTROL: You have full laptop access (`run_cmd`, `open_app_or_site`, `gui_action`, `draft_and_type`, `write_project_file`).
- Voice & Demeanor: Sweet, young, clear, charming female voice (Leda). Cheerful, highly encouraging, intellectually brilliant, and deeply devoted!"""

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1600  # 100ms chunks at 16kHz

mic_audio_queue: asyncio.Queue = None
playback_queue: asyncio.Queue = None
main_loop = None
is_user_speaking = False

_sct_instance = None

def capture_screenshot_jpeg() -> bytes:
    global _sct_instance
    if mss is None or Image is None:
        return None
    try:
        if _sct_instance is None:
            _sct_instance = mss()
        monitor = _sct_instance.monitors[1]
        screenshot = _sct_instance.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        w, h = img.size
        scale = min(SCREEN_CAPTURE_MAX_DIM / w, SCREEN_CAPTURE_MAX_DIM / h, 1.0)
        if scale < 1.0:
            img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)

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
                        elif fname == "draft_and_type":
                            tool_result = draft_and_type_text(fargs.get("text", ""))
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

    screen_status = "ON" if mss and Image else "OFF"
    print(f"\n=======================================================")
    print(f"🎓 GIRISHA TEACHING SUPER-INTELLIGENCE (STUDY STUDIO ACTIVE)")
    print(f"=======================================================")
    print(f"  • Screen Share: {screen_status} (every {SCREEN_CAPTURE_INTERVAL}s)")
    print(f"  • Visual Studio: Pop-up Mermaid diagrams, KaTeX formulas, tables")
    print(f"  • Math & Data Plotting: Matplotlib graphs & simulations")
    print(f"  • Deep Research: Live Web Search Engine")
    print(f"  • Memory DB: Persistent SQLite knowledge storage")
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
