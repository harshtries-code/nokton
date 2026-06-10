# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Nokton backend
# Build with: pyinstaller backend/nokton-backend.spec

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect hidden imports for key dependencies
hidden_imports = [
    # FastAPI + Uvicorn
    'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops',
    'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan',
    'uvicorn.lifespan.on', 'starlette', 'starlette.routing',
    'starlette.middleware', 'starlette.middleware.cors',
    'anyio', 'anyio._backends', 'anyio._backends._asyncio',

    # Pydantic
    'pydantic', 'pydantic.deprecated', 'pydantic.deprecated.decorator',

    # LLM providers
    'openai', 'anthropic', 'google.genai',

    # Voice pipeline
    'faster_whisper', 'openwakeword',
    'edge_tts', 'silero_vad',
    'numpy', 'pyaudio',

    # Desktop automation
    'pyautogui', 'psutil', 'mss', 'pyperclip',
    'pygetwindow', 'win32api', 'win32con', 'win32gui',

    # Web operations
    'requests', 'bs4', 'urllib3',

    # OCR
    'pytesseract', 'PIL',

    # Security
    'cryptography', 'cryptography.fernet',

    # Backend modules
    'backend', 'backend.main', 'backend.config',
    'backend.agent', 'backend.agent.engine',
    'backend.agent.conversation_manager', 'backend.agent.cost_tracker',
    'backend.agent.context_compressor', 'backend.agent.error_classifier',
    'backend.agent.interrupt_manager', 'backend.agent.skill_manager',
    'backend.agent.system_prompt',
    'backend.providers', 'backend.providers.base',
    'backend.providers.openrouter', 'backend.providers.openai',
    'backend.providers.anthropic', 'backend.providers.deepseek',
    'backend.providers.google', 'backend.providers.groq',
    'backend.providers.ollama', 'backend.providers.custom',
    'backend.providers.opencode', 'backend.providers.model_catalog',
    'backend.tools', 'backend.tools.registry', 'backend.tools.schema',
    'backend.tools.permission', 'backend.tools.file_ops',
    'backend.tools.web_ops', 'backend.tools.terminal',
    'backend.tools.app_control', 'backend.tools.clipboard_ops',
    'backend.tools.screenshot', 'backend.tools.system_info',
    'backend.tools.window_control',
    'backend.util', 'backend.util.api_key_manager',
    'backend.util.audit_logger', 'backend.util.format_utils',
    'backend.util.image_handler',
    'backend.voice', 'backend.voice.pipeline', 'backend.voice.stt',
    'backend.voice.tts', 'backend.voice.vad', 'backend.voice.wake_word',
]

# Entry point script
a = Analysis(
    ['run_backend.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('nokton.json', '.'),
        ('skills', 'skills'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'pandas',
        'jupyter', 'notebook', 'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nokton-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='nokton-backend',
)
