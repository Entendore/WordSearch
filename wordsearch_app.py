#!/usr/bin/env python3
"""
Word Search Puzzle Maker & Solver — PySide6 Desktop Application
================================================================
Enhanced edition with:
  - Difficulty presets (Kids / Easy / Medium / Hard / Expert) & themed word lists
  - Hint system (flash first letter, reveal word, auto-solve)
  - Save / Load puzzles in .wsp (JSON) format + PNG image export
  - Progress bar, score system, best-time leaderboard (persistent JSON)
  - Grid tooltips, selection-length preview, undo last find, keyboard shortcuts
  - Improved PDF export with custom title, difficulty badge, answer-key page
  - Dark mode toggle & zoom controls
  - Auto-size grid, live word-count badge, input validation
  - **Sound effects** on word found, completion, wrong guess, hints
  - **Local 2-player multiplayer** — turn-based race on a shared grid
  - **Round tracking** — best of 3 / 5 / 7 match play with auto-advance
  - **Pressure mode** — optional per-turn countdown timer (5s–120s)
  - **Dark mode grid painting** — grid adapts colors to dark/light theme
  - **Selection validity preview** — green/red selection based on word match
  - **Grid coordinate labels** — A-Z columns, 1-N rows for easy reference
  - **Re-generate button** — one-click new puzzle with same settings
  - **Pause/resume timer** — freeze the clock in single-player solver
  - **Custom word lists** — save/load reusable .wl files
  - **Smart retry generation** — auto-retries if too many words fail to place
  - **Improved found-words list** — unfound sorted to top, direction hints

Requirements:  pip install PySide6
               Audio: ffplay (bundled with ffmpeg) or aplay (Linux ALSA)
"""

import sys, random, string, math, json, time, struct, wave, io, threading, tempfile, os, platform, subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QSpinBox, QComboBox, QGroupBox, QTabWidget, QFileDialog,
    QMessageBox, QSizePolicy, QCheckBox, QSplitter, QFrame,
    QScrollArea, QStatusBar, QProgressBar, QToolBar, QSlider,
    QInputDialog, QListWidget, QListWidgetItem, QToolButton,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath,
    QAction, QKeySequence, QTextCursor, QIcon, QPixmap,
    QPalette, QRadialGradient, QLinearGradient
)

# ---------------------------------------------------------------------------
# Constants & Presets
# ---------------------------------------------------------------------------

DIRECTIONS = [
    (0, 1),   # right
    (1, 0),   # down
    (0, -1),  # left
    (-1, 0),  # up
    (1, 1),   # down-right
    (-1, -1), # up-left
    (1, -1),  # down-left
    (-1, 1),  # up-right
]

LETTERS = string.ascii_uppercase
STATS_FILE = Path.home() / ".wordsearch_stats.json"

DIFFICULTY_PRESETS = {
    "Kids": {
        "size": 8, "dirs": 2,
        "desc": "Right & Down only, small grid",
        "themes": {
            "Animals": ["CAT","DOG","FISH","BIRD","FROG","BEAR","LION","DUCK"],
            "Colors":  ["RED","BLUE","GREEN","YELLOW","PURPLE","ORANGE","PINK","BLACK"],
            "Food":    ["CAKE","MILK","BREAD","APPLE","CANDY","JUICE","PIZZA","CHEESE"],
            "Space":   ["STAR","MOON","SUN","MARS","EARTH","COMET","ORBIT","ROCKET"],
        }
    },
    "Easy": {
        "size": 10, "dirs": 4,
        "desc": "4 cardinal directions, medium grid",
        "themes": {
            "Nature":   ["RIVER","MOUNTAIN","FOREST","OCEAN","DESERT","ISLAND","VALLEY","STORM","CLOUD","LAKE"],
            "Sports":   ["SOCCER","TENNIS","HOCKEY","BOXING","RUGBY","GOLF","SWIM","RACE","TRACK","TEAM"],
            "Music":    ["PIANO","DRUM","GUITAR","VIOLIN","FLUTE","SONG","BEAT","TEMPO","LYRIC","CHORD"],
            "Science":  ["ATOM","CELL","LIGHT","MAGNET","ENERGY","FORCE","MASS","POWER","WAVE","HEAT"],
        }
    },
    "Medium": {
        "size": 14, "dirs": 6,
        "desc": "Cardinal + 2 diagonals, larger grid",
        "themes": {
            "Technology": ["PYTHON","CODING","ROBOT","SCREEN","PIXEL","BINARY","CURSOR","SERVER","DATABASE","PROGRAM","LAPTOP","NETWORK"],
            "Geography":  ["VOLCANO","GLACIER","CANYON","ISLAND","TUNDRA","PRAIRIE","PLATEAU","DELTA","FJORD","ATOLL","STEPPE","OASIS"],
            "History":    ["EMPIRE","CASTLE","KNIGHT","BATTLE","THRONE","TREATY","COLONY","VIKING","PHARAOH","SAMURAI","EMPEROR","DYNASTY"],
            "Ocean":      ["DOLPHIN","OCTOPUS","WHALE","CORAL","ANCHOR","SHELL","SHARK","SQUID","TIDE","HARBOR","KELP","SEAL"],
        }
    },
    "Hard": {
        "size": 18, "dirs": 8,
        "desc": "All 8 directions, large grid, many words",
        "themes": {
            "Languages": ["PYTHON","JAVA","SWIFT","RUST","RUBY","PERL","SCALA","KOTLIN","DART","HASKELL","LISP","FORTRAN","COBOL","BASIC"],
            "Anatomy":   ["SKELETON","MUSCLE","NEURON","ARTERY","VEIN","LIVER","KIDNEY","SPINE","CORTEX","RETINA","AORTA","TENDON","FEMUR","STERNUM"],
            "Cinema":    ["INCEPTION","GLADIATOR","AVATAR","TITANIC","JOKER","ROCKY","ALIEN","PSYCHO","JAWS","GODFATHER","MATRIX","VERTIGO","MULAN","FROZEN"],
        }
    },
    "Expert": {
        "size": 22, "dirs": 8,
        "desc": "All 8 directions, very large grid, long words",
        "themes": {
            "Literature":  ["HAMILTON","MACBETH","GATSBY","ODYSSEY","DONQUIXOTE","HAMLET","MOCKINGBIRD","HOBBIT","CHRISTMAS","TEMPEST","DRACULA","FRANKENSTEIN","OLIVER","ALICE"],
            "Technology+": ["ALGORITHM","BLOCKCHAIN","CYBERSECURITY","DATABASE","FRAMEWORK","COMPILER","PROTOCOL","ARCHITECTURE","DEBUGGING","FUNCTION","VARIABLE","TERMINAL","SOFTWARE","KEYBOARD"],
        }
    },
}

# Player color palettes for multiplayer
PLAYER_PALETTES = {
    1: [  # Blue / Cyan tones
        QColor(66, 133, 244, 160), QColor(0, 172, 193, 160),
        QColor(25, 118, 210, 160), QColor(2, 136, 209, 160),
        QColor(30, 136, 229, 160), QColor(66, 165, 245, 160),
    ],
    2: [  # Red / Orange / Pink tones
        QColor(234, 67, 53, 160), QColor(255, 112, 67, 160),
        QColor(211, 47, 47, 160), QColor(244, 67, 54, 160),
        QColor(239, 83, 80, 160), QColor(255, 138, 101, 160),
    ],
}

# ---------------------------------------------------------------------------
# Puzzle Generation Engine
# ---------------------------------------------------------------------------

def _generate_once(words, size, directions_count=8, max_attempts=500):
    """Single generation attempt (extracted for retry logic)."""
    words = sorted(set(w.upper().strip() for w in words if w.strip()), key=len, reverse=True)
    grid = [["" for _ in range(size)] for _ in range(size)]
    placements = []
    for word in words:
        placed = False
        attempts = max_attempts if len(word) > 6 else max_attempts // 2
        for _ in range(attempts):
            d = random.choice(DIRECTIONS[:directions_count])
            dr, dc = d
            end_r = (len(word) - 1) * dr
            end_c = (len(word) - 1) * dc
            r_range = range(max(0, -end_r), min(size, size - end_r))
            c_range = range(max(0, -end_c), min(size, size - end_c))
            if not r_range or not c_range:
                continue
            r = random.choice(r_range)
            c = random.choice(c_range)
            ok = True
            for i, ch in enumerate(word):
                cr, cc = r + i * dr, c + i * dc
                if grid[cr][cc] not in ("", ch):
                    ok = False
                    break
            if ok:
                for i, ch in enumerate(word):
                    grid[r + i * dr][c + i * dc] = ch
                placements.append({"word": word, "row": r, "col": c, "dr": dr, "dc": dc})
                placed = True
                break
    for r in range(size):
        for c in range(size):
            if grid[r][c] == "":
                grid[r][c] = random.choice(LETTERS)
    return grid, placements


def generate_word_search(words, size, directions_count=8, max_attempts=500,
                         smart_retry=True, min_placement_rate=0.85):
    grid, placements = _generate_once(words, size, directions_count, max_attempts)
    # Smart retry: if placement rate is too low, retry with shuffled word order
    if smart_retry and len(words) > 2:
        best_count = len(placements)
        for _ in range(3):
            shuffled = list(words)
            random.shuffle(shuffled)
            grid2, placements2 = _generate_once(shuffled, size, directions_count, max_attempts)
            if len(placements2) > best_count:
                grid, placements = grid2, placements2
                best_count = len(placements2)
                if best_count / len(words) >= min_placement_rate:
                    break
    return grid, placements


def auto_size(words, min_size=8, max_size=30):
    if not words:
        return 12
    longest = max(len(w) for w in words)
    total_letters = sum(len(w) for w in words)
    min_area = total_letters * 4
    min_dim = int(math.ceil(math.sqrt(min_area)))
    return max(longest + 2, min(min_dim, max_size))


# ---------------------------------------------------------------------------
# Stats / Leaderboard Persistence
# ---------------------------------------------------------------------------

def load_stats():
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except Exception:
            pass
    return {"best_times": {}, "puzzles_solved": 0, "total_time": 0}


def save_stats(stats):
    try:
        STATS_FILE.write_text(json.dumps(stats, indent=2))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Sound Effects Engine (procedural WAV generation)
# ---------------------------------------------------------------------------

class SoundManager:
    """Generates and plays procedural sound effects using pure Python + system audio."""

    def __init__(self):
        self._muted = False
        self._cache = {}
        self._backend = self._detect_backend()
        # Pre-generate all sounds
        self._generate_sounds()

    def _detect_backend(self):
        system = platform.system()
        if system == "Linux":
            for cmd in ("aplay", "paplay", "pw-play"):
                if os.path.exists(f"/usr/bin/{cmd}") or os.path.exists(f"/usr/local/bin/{cmd}"):
                    return ("cmd", cmd)
            # ffplay
            try:
                subprocess.run(["ffplay", "-version"], capture_output=True, timeout=3)
                return ("ffplay",)
            except Exception:
                pass
            return ("none",)
        elif system == "Darwin":
            return ("cmd", "afplay")
        elif system == "Windows":
            return ("winsound",)
        return ("none",)

    @staticmethod
    def _make_tone(frequency, duration=0.12, volume=0.4, sample_rate=22050, fade_out=True):
        n_samples = int(sample_rate * duration)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            attack = min(1.0, t / 0.008)
            decay = max(0.0, 1.0 - (t / duration)) if fade_out else 1.0
            env = attack * decay
            val = int(volume * 32767 * env * math.sin(2 * math.pi * frequency * t))
            val = max(-32768, min(32767, val))
            frames.extend(struct.pack('<h', val))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(frames))
        return buf.getvalue()

    @staticmethod
    def _make_chord(frequencies, note_duration=0.12, volume=0.35, sample_rate=22050):
        n_samples = int(sample_rate * note_duration * len(frequencies))
        frames = bytearray()
        for fi, freq in enumerate(frequencies):
            note_start = int(sample_rate * note_duration * fi)
            for i in range(int(sample_rate * note_duration)):
                t = i / sample_rate
                attack = min(1.0, t / 0.008)
                decay = max(0.0, 1.0 - t / note_duration)
                env = attack * decay
                val = int(volume * 32767 * env * math.sin(2 * math.pi * freq * t))
                val = max(-32768, min(32767, val))
                frames.extend(struct.pack('<h', val))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(frames))
        return buf.getvalue()

    @staticmethod
    def _make_sweep(f_start, f_end, duration=0.2, volume=0.35, sample_rate=22050):
        n_samples = int(sample_rate * duration)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            progress = t / duration
            freq = f_start + (f_end - f_start) * progress
            attack = min(1.0, t / 0.01)
            decay = max(0.0, 1.0 - progress ** 0.5)
            env = attack * decay
            val = int(volume * 32767 * env * math.sin(2 * math.pi * freq * t))
            val = max(-32768, min(32767, val))
            frames.extend(struct.pack('<h', val))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(frames))
        return buf.getvalue()

    def _generate_sounds(self):
        sr = 22050
        # Word found — bright ascending ding
        self._cache["found"] = self._make_sweep(600, 1200, 0.15, 0.35, sr)
        # Word found by player 2 — slightly different tone
        self._cache["found_p2"] = self._make_sweep(500, 1000, 0.15, 0.35, sr)
        # Completion fanfare — major chord arpeggio
        self._cache["complete"] = self._make_chord(
            [523, 659, 784, 1047], 0.18, 0.4, sr
        )
        # Wrong / miss — low buzz
        self._cache["miss"] = self._make_tone(180, 0.18, 0.25, sr)
        # Hint — soft chime
        self._cache["hint"] = self._make_tone(1047, 0.1, 0.2, sr)
        # Turn switch — quick click
        self._cache["turn"] = self._make_sweep(900, 700, 0.08, 0.2, sr)
        # Multiplayer win — triumphant fanfare
        self._cache["victory"] = self._make_chord(
            [392, 494, 587, 784, 988], 0.2, 0.4, sr
        )
        # Tick sound (low time warning)
        self._cache["tick"] = self._make_tone(880, 0.05, 0.15, sr)
        # Buzzer (time expired)
        self._cache["buzzer"] = self._make_tone(150, 0.3, 0.3, sr)
        # Round win — short fanfare
        self._cache["round_win"] = self._make_chord(
            [523, 659, 784], 0.15, 0.35, sr
        )
        # Match win — extended triumphant fanfare
        self._cache["match_win"] = self._make_chord(
            [392, 494, 587, 659, 784, 988, 1047], 0.18, 0.45, sr
        )

    def play(self, sound_name):
        if self._muted:
            return
        wav_data = self._cache.get(sound_name)
        if not wav_data:
            return
        threading.Thread(target=self._play_async, args=(wav_data,), daemon=True).start()

    def _play_async(self, wav_data):
        try:
            backend = self._backend
            if backend[0] == "cmd":
                proc = subprocess.Popen(
                    [backend[1], "-"],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                proc.communicate(input=wav_data, timeout=5)
            elif backend[0] == "ffplay":
                tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                tmp.write(wav_data)
                tmp.close()
                try:
                    subprocess.run(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
                    )
                finally:
                    try:
                        os.unlink(tmp.name)
                    except OSError:
                        pass
            elif backend[0] == "winsound":
                import winsound
                tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                tmp.write(wav_data)
                tmp.close()
                try:
                    winsound.PlaySound(tmp.name, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
        except Exception:
            pass  # Silently fail — sound is non-critical

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, val):
        self._muted = val


# Global sound manager (lazy-initialized)
_sound_manager = None

def get_sound_manager():
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


# ---------------------------------------------------------------------------
# Custom Widget: Interactive Grid for Solving
# ---------------------------------------------------------------------------

class GridWidget(QWidget):
    """Draws a letter grid and supports mouse-drag selection of words."""

    wordFound = Signal(str, int)   # (word, player_id)
    allFound = Signal()
    selectionChanged = Signal(str)
    missSelection = Signal()       # emitted on invalid selection release

    def __init__(self, parent=None, interactive=True):
        super().__init__(parent)
        self.grid = []
        self.placements = []
        self.found_words = set()
        self.word_set = set()
        self._interactive = interactive
        self._current_player = 0  # 0 = single player, 1 or 2 = multiplayer

        # Selection state
        self._selecting = False
        self._sel_start = None
        self._sel_end = None
        self._sel_cells = []
        self._hover_cell = None
        self._sel_is_valid = False  # True if current selection matches an unfound word

        # Zoom
        self._zoom = 1.0

        # Display options
        self._show_coords = True   # Show coordinate labels (A-Z, 1-N)
        self._dark_mode = False    # Tracks dark mode state

        # Default single-player palette
        self._palette = [
            QColor(66, 133, 244, 150), QColor(234, 67, 53, 150),
            QColor(52, 168, 83, 150), QColor(251, 188, 4, 150),
            QColor(171, 71, 188, 150), QColor(0, 172, 193, 150),
            QColor(255, 112, 67, 150), QColor(156, 204, 101, 150),
            QColor(255, 167, 38, 150), QColor(121, 134, 203, 150),
        ]
        self._color_map = {}        # word -> QColor
        self._player_map = {}       # word -> player_id
        self._color_idx_per_player = {0: 0, 1: 0, 2: 0}

        # Hint flash
        self._hint_cells = []
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.setInterval(2000)
        self._hint_timer.timeout.connect(self._clear_hint)

        # Undo stack
        self._undo_stack = []

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_grid(self, grid, placements=None):
        self.grid = grid
        self.placements = placements or []
        self.found_words = set()
        self._color_map = {}
        self._player_map = {}
        self._color_idx_per_player = {0: 0, 1: 0, 2: 0}
        self._sel_cells = []
        self._selecting = False
        self._sel_is_valid = False
        self._undo_stack = []
        self._hint_cells = []
        self.update()

    def set_word_set(self, words):
        self.word_set = set(w.upper() for w in words)

    def set_current_player(self, player_id):
        self._current_player = player_id

    def set_dark_mode(self, enabled):
        self._dark_mode = enabled
        self.update()

    def set_show_coords(self, show):
        self._show_coords = show
        self.update()

    def set_zoom(self, zoom):
        self._zoom = max(0.5, min(3.0, zoom))
        self.update()

    def get_player_words(self, player_id):
        return {w for w, p in self._player_map.items() if p == player_id}

    def _is_selection_valid_word(self):
        """Check if current _sel_cells spells an unfound word."""
        if not self._sel_cells or not self.grid:
            return False
        forward = "".join(self.grid[r][c] for r, c in self._sel_cells)
        backward = forward[::-1]
        return (forward in self.word_set and forward not in self.found_words) or \
               (backward in self.word_set and backward not in self.found_words)

    def _get_matched_word(self):
        """Return the matched word for current selection, or None."""
        if not self._sel_cells or not self.grid:
            return None
        forward = "".join(self.grid[r][c] for r, c in self._sel_cells)
        backward = forward[::-1]
        if forward in self.word_set and forward not in self.found_words:
            return forward
        if backward in self.word_set and backward not in self.found_words:
            return backward
        return None

    def undo_last(self):
        if self._undo_stack:
            word = self._undo_stack.pop()
            self.found_words.discard(word)
            player = self._player_map.pop(word, 0)
            # Re-adjust color index for that player
            self._color_map.pop(word, None)
            self.update()

    def show_hint_letter(self):
        unfound = self.word_set - self.found_words
        if not unfound:
            return
        word = random.choice(list(unfound))
        for p in self.placements:
            if p["word"] == word:
                self._hint_cells = [(p["row"], p["col"])]
                self._hint_timer.start()
                self.update()
                return
        first_ch = word[0]
        for r in range(len(self.grid)):
            for c in range(len(self.grid)):
                if self.grid[r][c] == first_ch:
                    self._hint_cells = [(r, c)]
                    self._hint_timer.start()
                    self.update()
                    return

    def reveal_word(self):
        unfound = self.word_set - self.found_words
        if not unfound:
            return
        word = random.choice(list(unfound))
        self._mark_found(word)

    def auto_solve(self):
        for word in sorted(self.word_set - self.found_words):
            self._mark_found(word)

    def _mark_found(self, word):
        self.found_words.add(word)
        player = self._current_player
        self._player_map[word] = player
        palette = PLAYER_PALETTES.get(player, self._palette) if player in (1, 2) else self._palette
        idx = self._color_idx_per_player.get(player, 0)
        color = QColor(palette[idx % len(palette)])
        self._color_idx_per_player[player] = idx + 1
        self._color_map[word] = color
        self.wordFound.emit(word, player)
        if self.found_words == self.word_set:
            self.allFound.emit()
        self.update()

    def _clear_hint(self):
        self._hint_cells = []
        self.update()

    # --- Geometry ---

    def _cell_size(self):
        if not self.grid:
            return 0
        w = self.width()
        h = self.height()
        n = len(self.grid)
        return (min(w, h) // (n + 1)) * self._zoom

    def _grid_origin(self):
        cs = self._cell_size()
        if cs == 0:
            return 0, 0
        n = len(self.grid)
        total = cs * n
        x = (self.width() - total) // 2
        y = (self.height() - total) // 2
        return x, y

    def _cell_at(self, pos):
        cs = self._cell_size()
        if cs == 0:
            return None
        ox, oy = self._grid_origin()
        c = int((pos.x() - ox) // cs)
        r = int((pos.y() - oy) // cs)
        n = len(self.grid)
        if 0 <= r < n and 0 <= c < n:
            return (r, c)
        return None

    def _line_cells(self, start, end):
        if start is None or end is None:
            return []
        r1, c1 = start
        r2, c2 = end
        dr = 0 if r2 == r1 else (1 if r2 > r1 else -1)
        dc = 0 if c2 == c1 else (1 if c2 > c1 else -1)
        if r1 != r2 and c1 != c2 and abs(r2 - r1) != abs(c2 - c1):
            return []
        length = max(abs(r2 - r1), abs(c2 - c1)) + 1
        return [(r1 + i * dr, c1 + i * dc) for i in range(length)]

    def _check_selection(self):
        if not self._sel_cells:
            return
        word = self._get_matched_word()
        if word:
            self._undo_stack.append(word)
            self._mark_found(word)

    # --- Mouse events ---

    def mousePressEvent(self, event):
        if not self._interactive:
            return
        if event.button() == Qt.LeftButton:
            cell = self._cell_at(event.position())
            if cell:
                self._selecting = True
                self._sel_start = cell
                self._sel_end = cell
                self._sel_cells = [cell]
                sel_text = self.grid[cell[0]][cell[1]]
                self.selectionChanged.emit(sel_text)
                self.update()

    def mouseMoveEvent(self, event):
        if not self._interactive:
            return
        cell = self._cell_at(event.position())
        if cell != self._hover_cell:
            self._hover_cell = cell
            self.update()
        if self._selecting and cell and cell != self._sel_end:
            self._sel_end = cell
            self._sel_cells = self._line_cells(self._sel_start, cell)
            self._sel_is_valid = self._is_selection_valid_word()
            sel_text = "".join(self.grid[r][c] for r, c in self._sel_cells)
            self.selectionChanged.emit(sel_text)
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._interactive:
            return
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            had_valid = self._sel_is_valid
            self._check_selection()
            # Emit miss signal if selection didn't match any word
            if not had_valid and self._sel_cells:
                self.missSelection.emit()
            self._sel_cells = []
            self._sel_is_valid = False
            self._sel_start = None
            self._sel_end = None
            self.selectionChanged.emit("")
            self.update()

    def leaveEvent(self, event):
        self._hover_cell = None
        self.update()

    def keyPressEvent(self, event):
        if not self._interactive:
            return
        if event.key() == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo_last()
        elif event.key() == Qt.Key_H:
            self.show_hint_letter()
        elif event.key() == Qt.Key_R and (event.modifiers() & Qt.ControlModifier):
            self.reveal_word()

    # --- Painting ---

    def paintEvent(self, event):
        if not self.grid:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cs = self._cell_size()
        ox, oy = self._grid_origin()
        n = len(self.grid)
        dm = self._dark_mode

        # Theme colors
        if dm:
            bg1, bg2 = QColor(30, 30, 46), QColor(24, 24, 37)
            grid_color = QColor(69, 71, 90)
            letter_color = QColor(205, 214, 244)
            hover_color = QColor(137, 180, 250, 60)
            coord_color = QColor(166, 173, 200)
            coord_bg = QColor(49, 50, 68, 180)
        else:
            bg1, bg2 = QColor(250, 250, 255), QColor(240, 242, 248)
            grid_color = QColor(190, 195, 210)
            letter_color = QColor(30, 30, 40)
            hover_color = QColor(200, 220, 255, 80)
            coord_color = QColor(95, 99, 104)
            coord_bg = QColor(241, 243, 244, 180)

        font_size = max(7, int(cs // 3))
        font = QFont("Consolas", font_size, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()

        # Background gradient
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0, bg1)
        bg.setColorAt(1, bg2)
        painter.fillRect(self.rect(), bg)

        # Coordinate labels
        if self._show_coords and cs > 12:
            coord_font = QFont("Arial", max(6, int(cs // 4)))
            painter.setFont(coord_font)
            cfm = painter.fontMetrics()
            painter.setPen(QPen(coord_color))
            for i in range(n):
                # Column labels (A, B, C...)
                col_label = chr(ord('A') + i) if i < 26 else str(i)
                tr = cfm.boundingRect(col_label)
                cx = ox + i * cs + (cs - tr.width()) / 2
                cy = oy - int(cs * 0.1)
                painter.setBrush(QBrush(coord_bg))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(QRectF(ox + i * cs, oy - cs * 0.5, cs, cs * 0.45), 2, 2)
                painter.setPen(QPen(coord_color))
                painter.drawText(QPointF(cx, cy), col_label)
                # Row labels (1, 2, 3...)
                row_label = str(i + 1)
                tr = cfm.boundingRect(row_label)
                rx = ox - cs * 0.5 + (cs * 0.45 - tr.width()) / 2
                ry = oy + i * cs + (cs + tr.height()) / 2 - cfm.descent()
                painter.setBrush(QBrush(coord_bg))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(QRectF(ox - cs * 0.5, oy + i * cs, cs * 0.45, cs), 2, 2)
                painter.setPen(QPen(coord_color))
                painter.drawText(QPointF(rx, ry), row_label)
            painter.setFont(font)

        # Draw found-word highlights
        for word, color in self._color_map.items():
            for p in self.placements:
                if p["word"] == word:
                    self._paint_word_highlight(painter, p, color, cs, ox, oy)
                    break

        # Draw hint flash cells
        if self._hint_cells:
            pulse = 150 + int(80 * math.sin(time.time() * 8))
            hint_color = QColor(255, 152, 0, pulse)
            painter.setBrush(QBrush(hint_color))
            painter.setPen(QPen(QColor(255, 87, 34), 2))
            for r, c in self._hint_cells:
                painter.drawRoundedRect(
                    QRectF(ox + c * cs + 1, oy + r * cs + 1, cs - 2, cs - 2), 6, 6
                )
            if self._hint_timer.isActive():
                QTimer.singleShot(50, self.update)

        # Draw hover highlight
        if self._hover_cell and self._interactive:
            r, c = self._hover_cell
            painter.setBrush(QBrush(hover_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(
                QRectF(ox + c * cs + 1, oy + r * cs + 1, cs - 2, cs - 2), 3, 3
            )

        # Draw current selection highlight with validity coloring
        if self._sel_cells:
            if self._sel_is_valid:
                sel_color1 = QColor(52, 168, 83, 160)
                sel_color2 = QColor(27, 94, 32, 160)
            elif self._current_player == 1:
                sel_color1 = QColor(66, 133, 244, 140)
                sel_color2 = QColor(25, 118, 210, 140)
            elif self._current_player == 2:
                sel_color1 = QColor(234, 67, 53, 140)
                sel_color2 = QColor(211, 47, 47, 140)
            else:
                sel_color1 = QColor(255, 235, 59, 120)
                sel_color2 = QColor(255, 193, 7, 120)
            sel_brush = QLinearGradient(
                ox + self._sel_cells[0][1] * cs, oy + self._sel_cells[0][0] * cs,
                ox + self._sel_cells[-1][1] * cs, oy + self._sel_cells[-1][0] * cs
            )
            sel_brush.setColorAt(0, sel_color1)
            sel_brush.setColorAt(1, sel_color2)
            painter.setBrush(QBrush(sel_brush))
            painter.setPen(Qt.NoPen)
            for r, c in self._sel_cells:
                painter.drawRoundedRect(
                    QRectF(ox + c * cs + 1, oy + r * cs + 1, cs - 2, cs - 2), 4, 4
                )

        # Draw grid lines
        painter.setPen(QPen(grid_color, 1))
        for i in range(n + 1):
            painter.drawLine(QPointF(ox + i * cs, oy), QPointF(ox + i * cs, oy + n * cs))
            painter.drawLine(QPointF(ox, oy + i * cs), QPointF(ox + n * cs, oy + i * cs))

        # Draw letters
        painter.setFont(font)
        for r in range(n):
            for c in range(n):
                text = self.grid[r][c]
                in_found = any(
                    (r, c) in self._get_cells_for_word(w) for w in self.found_words
                )
                if in_found:
                    painter.setPen(QPen(QColor(255, 255, 255)))
                else:
                    painter.setPen(QPen(letter_color))
                tr = fm.boundingRect(text)
                tx = ox + c * cs + (cs - tr.width()) / 2
                ty = oy + r * cs + (cs + tr.height()) / 2 - fm.descent()
                painter.drawText(QPointF(tx, ty), text)

        painter.end()

    def _get_cells_for_word(self, word):
        for p in self.placements:
            if p["word"] == word:
                r, c, dr, dc = p["row"], p["col"], p["dr"], p["dc"]
                return {(r + i * dr, c + i * dc) for i in range(len(word))}
        return set()

    def _paint_word_highlight(self, painter, placement, color, cs, ox, oy):
        r, c = placement["row"], placement["col"]
        dr, dc = placement["dr"], placement["dc"]
        length = len(placement["word"])
        cells = [(r + i * dr, c + i * dc) for i in range(length)]
        min_r = min(cr for cr, cc in cells)
        max_r = max(cr for cr, cc in cells)
        min_c = min(cc for cr, cc in cells)
        max_c = max(cc for cr, cc in cells)
        x1 = ox + min_c * cs + 2
        y1 = oy + min_r * cs + 2
        x2 = ox + (max_c + 1) * cs - 2
        y2 = oy + (max_r + 1) * cs - 2
        radius = cs / 2.5
        path = QPainterPath()
        path.addRoundedRect(QRectF(x1, y1, x2 - x1, y2 - y1), radius, radius)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)


# ---------------------------------------------------------------------------
# Maker Tab  (unchanged from previous version)
# ---------------------------------------------------------------------------

class MakerTab(QWidget):
    puzzleReady = Signal(list, list, int, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._current_grid = []
        self._current_placements = []
        self._current_size = 12
        self._current_title = "WORD SEARCH PUZZLE"
        self._current_difficulty = "Medium"

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        left = QVBoxLayout()
        left.setSpacing(10)

        grp_title = QGroupBox("Puzzle Title")
        tl = QHBoxLayout(grp_title)
        self.title_input = QLineEdit("WORD SEARCH PUZZLE")
        self.title_input.setFont(QFont("Arial", 11))
        self.title_input.setPlaceholderText("Enter puzzle title...")
        tl.addWidget(self.title_input)
        left.addWidget(grp_title)

        grp_diff = QGroupBox("Difficulty & Theme")
        dl = QGridLayout(grp_diff)
        dl.addWidget(QLabel("Difficulty:"), 0, 0)
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(DIFFICULTY_PRESETS.keys())
        self.diff_combo.setCurrentText("Medium")
        self.diff_combo.currentTextChanged.connect(self._on_difficulty_changed)
        dl.addWidget(self.diff_combo, 0, 1)
        dl.addWidget(QLabel("Theme:"), 1, 0)
        self.theme_combo = QComboBox()
        self._populate_themes("Medium")
        self.theme_combo.currentTextChanged.connect(self._on_theme_selected)
        dl.addWidget(self.theme_combo, 1, 1)
        self.load_theme_btn = QPushButton("Load Theme Words")
        self.load_theme_btn.clicked.connect(self._on_theme_selected)
        dl.addWidget(self.load_theme_btn, 2, 0, 1, 2)
        self.diff_desc_label = QLabel(DIFFICULTY_PRESETS["Medium"]["desc"])
        self.diff_desc_label.setStyleSheet("color:#666; font-style:italic; font-size:11px")
        self.diff_desc_label.setWordWrap(True)
        dl.addWidget(self.diff_desc_label, 3, 0, 1, 2)
        left.addWidget(grp_diff)

        grp_words = QGroupBox("Words")
        wl = QVBoxLayout(grp_words)
        self.words_input = QTextEdit()
        self.words_input.setPlaceholderText("Enter words, one per line:\n\nPYTHON\nPUZZLE\nSEARCH\nGRID\nSOLVE\n...")
        self.words_input.setFont(QFont("Consolas", 11))
        self.words_input.setMinimumHeight(150)
        wl.addWidget(self.words_input)
        bot_row = QHBoxLayout()
        self.word_count_label = QLabel("Words: 0")
        self.word_count_label.setStyleSheet("font-weight:bold; color:#4285f4")
        self.words_input.textChanged.connect(self._on_words_changed)
        bot_row.addWidget(self.word_count_label)
        self.auto_size_btn = QPushButton("Auto-Size Grid")
        self.auto_size_btn.setToolTip("Calculate optimal grid size for your word list")
        self.auto_size_btn.clicked.connect(self._on_auto_size)
        bot_row.addWidget(self.auto_size_btn)
        bot_row.addStretch()
        wl.addLayout(bot_row)
        left.addWidget(grp_words, 1)

        grp_settings = QGroupBox("Grid Settings")
        sl = QGridLayout(grp_settings)
        sl.addWidget(QLabel("Grid Size:"), 0, 0)
        size_row = QHBoxLayout()
        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 40)
        self.size_spin.setValue(14)
        self.size_spin.setSuffix(" x N")
        size_row.addWidget(self.size_spin)
        self.auto_size_label = QPushButton("Auto")
        self.auto_size_label.setMaximumWidth(60)
        self.auto_size_label.setToolTip("Auto-calculate best grid size")
        self.auto_size_label.clicked.connect(self._on_auto_size)
        size_row.addWidget(self.auto_size_label)
        sl.addLayout(size_row, 0, 1)
        sl.addWidget(QLabel("Directions:"), 1, 0)
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["Right only","Right & Down","Right, Down, Left",
            "4 cardinal directions","4 cardinal + 1 diagonal","4 cardinal + 2 diagonals","All 8 directions"])
        self.dir_combo.setCurrentIndex(5)
        sl.addWidget(self.dir_combo, 1, 1)
        left.addWidget(grp_settings)

        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Puzzle")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.setStyleSheet("QPushButton{background:#4285f4;color:white;font-size:14px;font-weight:bold;border-radius:6px;padding:8px}QPushButton:hover{background:#3367d6}QPushButton:pressed{background:#2a5eb5}")
        self.generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self.generate_btn)
        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.setMinimumHeight(42)
        self.regenerate_btn.setEnabled(False)
        self.regenerate_btn.setStyleSheet("QPushButton{background:#34a853;color:white;font-size:14px;font-weight:bold;border-radius:6px;padding:8px}QPushButton:hover{background:#2d8e47}QPushButton:pressed{background:#246b36}")
        self.regenerate_btn.setToolTip("Generate a new puzzle with the same settings")
        self.regenerate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self.regenerate_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(42)
        self.clear_btn.setStyleSheet("QPushButton{background:#f1f3f4;font-size:14px;border-radius:6px;padding:8px}QPushButton:hover{background:#d2d5d9}")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)
        left.addLayout(btn_row)

        action_row = QHBoxLayout()
        self.export_pdf_btn = QPushButton("Export PDF")
        self.export_pdf_btn.setEnabled(False)
        self.export_pdf_btn.setMinimumHeight(36)
        self.export_pdf_btn.setStyleSheet("QPushButton{background:#34a853;color:white;font-size:12px;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#2d8e47}")
        self.export_pdf_btn.clicked.connect(self._on_export_pdf)
        action_row.addWidget(self.export_pdf_btn)
        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setMinimumHeight(36)
        self.export_png_btn.setStyleSheet("QPushButton{background:#ea4335;color:white;font-size:12px;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#c5362b}")
        self.export_png_btn.clicked.connect(self._on_export_png)
        action_row.addWidget(self.export_png_btn)
        self.save_btn = QPushButton("Save .wsp")
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(36)
        self.save_btn.setStyleSheet("QPushButton{background:#fbbc05;color:#3c4043;font-size:12px;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#f0b400}")
        self.save_btn.clicked.connect(self._on_save)
        action_row.addWidget(self.save_btn)
        left.addLayout(action_row)

        self.send_to_solver_btn = QPushButton("Send to Solver")
        self.send_to_solver_btn.setEnabled(False)
        self.send_to_solver_btn.setMinimumHeight(38)
        self.send_to_solver_btn.setStyleSheet("QPushButton{background:#4285f4;color:white;font-size:13px;font-weight:bold;border-radius:6px;padding:8px}QPushButton:hover{background:#3367d6}")
        left.addWidget(self.send_to_solver_btn)

        self.send_to_multi_btn = QPushButton("Send to Multiplayer")
        self.send_to_multi_btn.setEnabled(False)
        self.send_to_multi_btn.setMinimumHeight(38)
        self.send_to_multi_btn.setStyleSheet("QPushButton{background:#9c27b0;color:white;font-size:13px;font-weight:bold;border-radius:6px;padding:8px}QPushButton:hover{background:#7b1fa2}")
        left.addWidget(self.send_to_multi_btn)

        left_panel = QWidget()
        left_panel.setLayout(left)
        left_panel.setFixedWidth(360)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        right = QVBoxLayout()
        right.addWidget(QLabel("Preview"))
        self.preview = GridWidget(interactive=False)
        right.addWidget(self.preview, 1)
        self.word_list_label = QLabel("")
        self.word_list_label.setWordWrap(True)
        self.word_list_label.setStyleSheet("padding:4px; background:#f8f9fa; border-radius:4px")
        right.addWidget(self.word_list_label)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        right_w = QWidget()
        right_w.setLayout(right)
        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer = QHBoxLayout(self)
        outer.addWidget(splitter)

    def _populate_themes(self, difficulty):
        self.theme_combo.clear()
        preset = DIFFICULTY_PRESETS.get(difficulty, {})
        themes = preset.get("themes", {})
        self.theme_combo.addItems(list(themes.keys()))
        if themes:
            self.diff_desc_label.setText(preset.get("desc", ""))

    def _on_difficulty_changed(self, diff):
        preset = DIFFICULTY_PRESETS.get(diff, {})
        self.size_spin.setValue(preset.get("size", 12))
        dirs = preset.get("dirs", 8)
        dir_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 6}
        self.dir_combo.setCurrentIndex(dir_map.get(dirs, 6))
        self._populate_themes(diff)
        self.diff_desc_label.setText(preset.get("desc", ""))

    def _on_theme_selected(self, theme=None):
        if not theme:
            theme = self.theme_combo.currentText()
        diff = self.diff_combo.currentText()
        preset = DIFFICULTY_PRESETS.get(diff, {})
        themes = preset.get("themes", {})
        if theme in themes:
            self.words_input.setPlainText("\n".join(themes[theme]))
            self._on_auto_size()

    def _on_words_changed(self):
        text = self.words_input.toPlainText().strip()
        words = [w.strip() for w in text.splitlines() if w.strip()]
        unique = set(w.upper() for w in words)
        self.word_count_label.setText(f"Words: {len(words)} ({len(unique)} unique)")
        if len(words) != len(unique):
            self.word_count_label.setStyleSheet("font-weight:bold; color:#ea4335")
        else:
            self.word_count_label.setStyleSheet("font-weight:bold; color:#4285f4")

    def _on_auto_size(self):
        text = self.words_input.toPlainText().strip()
        words = [w.strip() for w in text.splitlines() if w.strip()]
        if words:
            self.size_spin.setValue(auto_size(words))

    def _dir_count_real(self):
        mapping = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 8}
        return mapping.get(self.dir_combo.currentIndex(), 8)

    def _on_generate(self):
        text = self.words_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Words", "Please enter at least one word.")
            return
        words = [w.strip() for w in text.splitlines() if w.strip()]
        size = self.size_spin.value()
        upper_words = [w.upper() for w in words]
        dupes = [w for w in upper_words if upper_words.count(w) > 1]
        if dupes:
            if not QMessageBox.question(self, "Duplicate Words",
                f"These words appear more than once:\n{', '.join(set(dupes))}\n\nRemove duplicates?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                return
            seen = set()
            unique_words = []
            for w in words:
                if w.upper() not in seen:
                    seen.add(w.upper())
                    unique_words.append(w)
            words = unique_words
        too_long = [w for w in words if len(w) > size]
        if too_long:
            if not QMessageBox.question(self, "Long Words",
                f"These words exceed grid size ({size}):\n{', '.join(too_long)}\n\nRemove them?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                return
            words = [w for w in words if len(w) <= size]
        if not words:
            QMessageBox.warning(self, "No Valid Words", "No words left to place.")
            return
        dirs = self._dir_count_real()
        grid, placements = generate_word_search(words, size, directions_count=dirs)
        self._current_grid = grid
        self._current_placements = placements
        self._current_size = size
        self._current_title = self.title_input.text().strip() or "WORD SEARCH PUZZLE"
        self._current_difficulty = self.diff_combo.currentText()
        self.preview.set_grid(grid, placements)
        self.preview.set_word_set([p["word"] for p in placements])
        placed_names = [p["word"] for p in placements]
        missing = [w for w in words if w.upper() not in placed_names]
        lines = [f"Placed: {len(placed_names)}/{len(words)} words", f"Difficulty: {self._current_difficulty}", f"Grid: {size} x {size}"]
        if missing:
            lines.append(f"Could not place: {', '.join(missing)}")
        self.word_list_label.setText("\n".join(lines))
        for btn in (self.export_pdf_btn, self.export_png_btn, self.save_btn, self.send_to_solver_btn, self.send_to_multi_btn, self.regenerate_btn):
            btn.setEnabled(True)
        self.puzzleReady.emit(grid, placements, size, self._current_title, self._current_difficulty)

    def _on_clear(self):
        self.words_input.clear()
        self.preview.set_grid([])
        self.word_list_label.setText("")
        self.word_count_label.setText("Words: 0")
        for btn in (self.export_pdf_btn, self.export_png_btn, self.save_btn, self.send_to_solver_btn, self.send_to_multi_btn, self.regenerate_btn):
            btn.setEnabled(False)

    def _on_export_pdf(self):
        if not self._current_grid:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "wordsearch_puzzle.pdf", "PDF Files (*.pdf);;All Files (*)")
        if not path:
            return
        self._render_pdf(path, include_answer_key=True)
        QMessageBox.information(self, "Exported", f"Puzzle saved to:\n{path}")

    def _render_pdf(self, path, include_answer_key=False):
        from PySide6.QtGui import QPageSize
        from PySide6.QtPrintSupport import QPrinter
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        printer.setFullPage(True)
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing)
        page = printer.pageRect(QPrinter.Unit.Point)
        margin = 45
        pw = page.width() - 2 * margin
        ph = page.height() - 2 * margin
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(66, 133, 244)))
        painter.drawRect(QRectF(0, 0, page.width(), 8))
        painter.setBrush(QBrush(QColor(234, 67, 53)))
        painter.drawRect(QRectF(0, 8, page.width(), 3))
        y_offset = margin
        title_font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(30, 30, 30)))
        painter.drawText(QRectF(margin, y_offset, pw, 30), Qt.AlignLeft, self._current_title)
        y_offset += 35
        diff = self._current_difficulty
        badge_colors = {"Kids": QColor(52,168,83),"Easy": QColor(66,133,244),"Medium": QColor(251,188,4),"Hard": QColor(234,67,53),"Expert": QColor(156,39,176)}
        badge_color = badge_colors.get(diff, QColor(100,100,100))
        painter.setBrush(QBrush(badge_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(margin, y_offset, 80, 22), 11, 11)
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRectF(margin, y_offset, 80, 22), Qt.AlignCenter, diff.upper())
        y_offset += 30
        grid = self._current_grid
        n = len(grid)
        available_h = ph - (y_offset - margin) - 80
        cell = min((pw * 0.85) / n, available_h / n)
        cell = max(cell, 8)
        gw = cell * n
        gh = cell * n
        gx = margin + (pw - gw) / 2
        gy = y_offset + 5
        painter.setBrush(QBrush(QColor(248, 249, 255)))
        painter.setPen(QPen(QColor(180, 185, 200), 0.8))
        painter.drawRoundedRect(QRectF(gx - 4, gy - 4, gw + 8, gh + 8), 4, 4)
        grid_font = QFont("Consolas", max(7, cell * 0.6), QFont.Bold)
        painter.setFont(grid_font)
        fm = painter.fontMetrics()
        painter.setPen(QPen(QColor(200, 205, 215), 0.5))
        for i in range(n + 1):
            painter.drawLine(QPointF(gx + i * cell, gy), QPointF(gx + i * cell, gy + gh))
            painter.drawLine(QPointF(gx, gy + i * cell), QPointF(gx + gw, gy + i * cell))
        painter.setPen(QPen(QColor(30, 30, 40)))
        for r in range(n):
            for c in range(n):
                text = grid[r][c]
                tr = fm.boundingRect(text)
                tx = gx + c * cell + (cell - tr.width()) / 2
                ty = gy + r * cell + (cell + tr.height()) / 2 - fm.descent()
                painter.drawText(QPointF(tx, ty), text)
        word_y = gy + gh + 20
        painter.setPen(QPen(QColor(60, 60, 60)))
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(QRectF(margin, word_y, pw, 16), Qt.AlignLeft, "FIND THESE WORDS:")
        word_y += 18
        painter.setFont(QFont("Consolas", 10))
        words = [p["word"] for p in self._current_placements]
        cols = max(2, min(4, int(pw / 120)))
        col_w = pw / cols
        for i, w in enumerate(sorted(words)):
            col = i % cols
            row = i // cols
            painter.drawText(QPointF(margin + col * col_w, word_y + row * 16), w)
        if include_answer_key:
            printer.newPage()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(156, 39, 176)))
            painter.drawRect(QRectF(0, 0, page.width(), 8))
            painter.setBrush(QBrush(QColor(103, 58, 183)))
            painter.drawRect(QRectF(0, 8, page.width(), 3))
            painter.setPen(QPen(QColor(30, 30, 30)))
            painter.setFont(QFont("Arial", 20, QFont.Bold))
            painter.drawText(QRectF(margin, margin, pw, 30), Qt.AlignLeft, "ANSWER KEY")
            y_off = margin + 55
            ans_cell = min((pw * 0.85) / n, (ph - 80) / n)
            ans_cell = max(ans_cell, 7)
            ans_gw = ans_cell * n
            ans_gh = ans_cell * n
            ans_gx = margin + (pw - ans_gw) / 2
            ans_gy = y_off
            answer_colors = [QColor(66,133,244,100),QColor(234,67,53,100),QColor(52,168,83,100),QColor(251,188,4,100),QColor(171,71,188,100),QColor(0,172,193,100),QColor(255,112,67,100),QColor(156,204,101,100)]
            for idx, p in enumerate(self._current_placements):
                color = answer_colors[idx % len(answer_colors)]
                r, c, dr, dc = p["row"], p["col"], p["dr"], p["dc"]
                for i in range(len(p["word"])):
                    cr, cc = r + i * dr, c + i * dc
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(QRectF(ans_gx+cc*ans_cell+1,ans_gy+cr*ans_cell+1,ans_cell-2,ans_cell-2),3,3)
            painter.setPen(QPen(QColor(180,180,180),0.5))
            for i in range(n+1):
                painter.drawLine(QPointF(ans_gx+i*ans_cell,ans_gy),QPointF(ans_gx+i*ans_cell,ans_gy+ans_gh))
                painter.drawLine(QPointF(ans_gx,ans_gy+i*ans_cell),QPointF(ans_gx+ans_gw,ans_gy+i*ans_cell))
            ans_font = QFont("Consolas", max(6, ans_cell*0.55), QFont.Bold)
            painter.setFont(ans_font)
            afm = painter.fontMetrics()
            painter.setPen(QPen(QColor(30,30,30)))
            for r in range(n):
                for c in range(n):
                    text = grid[r][c]
                    tr = afm.boundingRect(text)
                    tx = ans_gx+c*ans_cell+(ans_cell-tr.width())/2
                    ty = ans_gy+r*ans_cell+(ans_cell+tr.height())/2-afm.descent()
                    painter.drawText(QPointF(tx,ty), text)
            wl_y = ans_gy+ans_gh+15
            painter.setFont(QFont("Consolas",9))
            dir_symbols = {(0,1):"\u2192",(1,0):"\u2193",(0,-1):"\u2190",(-1,0):"\u2191",(1,1):"\u2198",(-1,-1):"\u2196",(1,-1):"\u2199",(-1,1):"\u2197"}
            for i, w in enumerate(sorted(self._current_placements, key=lambda p: p["word"])):
                sym = dir_symbols.get((w["dr"],w["dc"]),"?")
                col = i % 3
                row = i // 3
                painter.drawText(QPointF(margin+col*(pw/3), wl_y+row*15), f"{w['word']} {sym}")
        painter.end()

    def _on_export_png(self):
        if not self._current_grid:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "wordsearch_puzzle.png", "PNG Images (*.png);;All Files (*)")
        if not path:
            return
        self._render_png(path)
        QMessageBox.information(self, "Exported", f"Image saved to:\n{path}")

    def _render_png(self, path):
        grid = self._current_grid; n = len(grid); cell = 40; margin = 60
        grid_px = cell * n
        total_w = grid_px + 2 * margin; total_h = grid_px + 2 * margin + 120
        pixmap = QPixmap(total_w, total_h); pixmap.fill(QColor(255, 255, 255))
        p = QPainter(pixmap); p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Arial", 18, QFont.Bold)); p.setPen(QPen(QColor(30, 30, 30)))
        p.drawText(QRectF(margin, 15, total_w - 2 * margin, 30), Qt.AlignCenter, self._current_title)
        gx, gy = margin, 55
        p.setBrush(QBrush(QColor(248, 249, 255))); p.setPen(QPen(QColor(180, 185, 200), 1))
        p.drawRoundedRect(QRectF(gx-4, gy-4, grid_px+8, grid_px+8), 6, 6)
        p.setPen(QPen(QColor(200, 205, 215), 0.8))
        for i in range(n+1):
            p.drawLine(gx+i*cell, gy, gx+i*cell, gy+grid_px)
            p.drawLine(gx, gy+i*cell, gx+grid_px, gy+i*cell)
        p.setFont(QFont("Consolas", cell//2, QFont.Bold)); p.setPen(QPen(QColor(30, 30, 40)))
        fm = p.fontMetrics()
        for r in range(n):
            for c in range(n):
                text = grid[r][c]; tr = fm.boundingRect(text)
                tx = gx+c*cell+(cell-tr.width())/2; ty = gy+r*cell+(cell+tr.height())/2-fm.descent()
                p.drawText(QPointF(tx, ty), text)
        wy = gy+grid_px+15; p.setFont(QFont("Consolas", 11))
        words = sorted(p["word"] for p in self._current_placements)
        cols = max(2, total_w//130); col_w = (total_w-2*margin)/cols
        for i, w in enumerate(words):
            col = i%cols; row = i//cols
            p.drawText(QPointF(margin+col*col_w, wy+row*18), w)
        p.end(); pixmap.save(path)

    def _on_save(self):
        if not self._current_grid: return
        path, _ = QFileDialog.getSaveFileName(self, "Save Puzzle", "puzzle.wsp", "Word Search Puzzle (*.wsp);;JSON Files (*.json);;All Files (*)")
        if not path: return
        data = {"title": self._current_title, "difficulty": self._current_difficulty, "grid": self._current_grid, "placements": self._current_placements, "words": [p["word"] for p in self._current_placements]}
        try:
            Path(path).write_text(json.dumps(data, indent=2))
            QMessageBox.information(self, "Saved", f"Puzzle saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def get_puzzle_data(self):
        words = [p["word"] for p in self._current_placements]
        return self._current_grid, words, self._current_size, self._current_placements


# ---------------------------------------------------------------------------
# Solver Tab
# ---------------------------------------------------------------------------

class SolverTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._elapsed = 0
        self._hints_used = 0
        self._reveals_used = 0
        self._stats = load_stats()
        self._snd = get_sound_manager()
        self._paused = False

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        grid_layout = QVBoxLayout()
        header = QHBoxLayout()
        header.addWidget(QLabel("Puzzle Grid"))
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.timer_label.setStyleSheet("color:#4285f4; padding:4px 12px; background:#e8f0fe; border-radius:6px")
        header.addStretch()
        header.addWidget(self.timer_label)
        grid_layout.addLayout(header)
        self.selection_label = QLabel("")
        self.selection_label.setFont(QFont("Consolas", 13, QFont.Bold))
        self.selection_label.setStyleSheet("color:#5f6368; padding:4px 8px; min-height:28px; background:#f1f3f4; border-radius:4px")
        self.selection_label.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(self.selection_label)
        self.grid_widget = GridWidget(interactive=True)
        self.grid_widget.wordFound.connect(self._on_word_found)
        self.grid_widget.allFound.connect(self._on_all_found)
        self.grid_widget.selectionChanged.connect(self._on_selection_changed)
        self.grid_widget.missSelection.connect(self._on_miss)
        grid_layout.addWidget(self.grid_widget, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m  (%p%)")
        self.progress_bar.setStyleSheet("QProgressBar{border:1px solid #dadce0;border-radius:6px;text-align:center;height:22px}QProgressBar::chunk{background:#4285f4;border-radius:5px}")
        grid_layout.addWidget(self.progress_bar)
        ctrl1 = QHBoxLayout()
        self.load_btn = QPushButton("Load .wsp / .txt")
        self.load_btn.clicked.connect(self._on_load_file)
        ctrl1.addWidget(self.load_btn)
        self.paste_btn = QPushButton("Paste Grid")
        self.paste_btn.clicked.connect(self._on_paste)
        ctrl1.addWidget(self.paste_btn)
        self.load_wsp_btn = QPushButton("Open .wsp")
        self.load_wsp_btn.clicked.connect(self._on_load_wsp)
        ctrl1.addWidget(self.load_wsp_btn)
        grid_layout.addLayout(ctrl1)
        ctrl2 = QHBoxLayout()
        self.hint_btn = QPushButton("Hint (H)")
        self.hint_btn.setToolTip("Flash the first letter of a random unfound word (shortcut: H)")
        self.hint_btn.setStyleSheet("QPushButton{background:#ff9800;color:white;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#f57c00}")
        self.hint_btn.clicked.connect(self._on_hint)
        ctrl2.addWidget(self.hint_btn)
        self.reveal_btn = QPushButton("Reveal (Ctrl+R)")
        self.reveal_btn.setStyleSheet("QPushButton{background:#ea4335;color:white;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#c5362b}")
        self.reveal_btn.clicked.connect(self._on_reveal)
        ctrl2.addWidget(self.reveal_btn)
        self.auto_solve_btn = QPushButton("Auto-Solve")
        self.auto_solve_btn.setStyleSheet("QPushButton{background:#9c27b0;color:white;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#7b1fa2}")
        self.auto_solve_btn.clicked.connect(self._on_auto_solve)
        ctrl2.addWidget(self.auto_solve_btn)
        grid_layout.addLayout(ctrl2)
        ctrl2b = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setToolTip("Pause/resume the timer (Ctrl+P)")
        self.pause_btn.setStyleSheet("QPushButton{background:#fbbc05;color:#3c4043;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#f0b400}QPushButton:checked{background:#ea4335;color:white}")
        self.pause_btn.clicked.connect(self._on_pause_toggle)
        ctrl2b.addWidget(self.pause_btn)
        self.miss_label = QLabel("")
        self.miss_label.setStyleSheet("color:#ea4335; font-size:11px; padding:2px 4px")
        ctrl2b.addWidget(self.miss_label)
        ctrl2b.addStretch()
        grid_layout.addLayout(ctrl2b)
        ctrl3 = QHBoxLayout()
        self.undo_btn = QPushButton("Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.grid_widget.undo_last)
        ctrl3.addWidget(self.undo_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)
        self.reset_btn.setStyleSheet("QPushButton{background:#f1f3f4;border-radius:6px;padding:6px}QPushButton:hover{background:#d2d5d9}")
        ctrl3.addWidget(self.reset_btn)
        ctrl3.addStretch()
        ctrl3.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(120)
        self.zoom_slider.valueChanged.connect(lambda v: self.grid_widget.set_zoom(v / 100.0))
        ctrl3.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("100%")
        self.zoom_slider.valueChanged.connect(lambda v: self.zoom_label.setText(f"{v}%"))
        ctrl3.addWidget(self.zoom_label)
        grid_layout.addLayout(ctrl3)

        right = QVBoxLayout()
        self.score_label = QLabel("Score: 0")
        self.score_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.score_label.setStyleSheet("color:#1a73e8; padding:6px; background:#e8f0fe; border-radius:6px")
        self.score_label.setAlignment(Qt.AlignCenter)
        right.addWidget(self.score_label)
        right.addWidget(QLabel("Words to Find"))
        self.word_list_input = QTextEdit()
        self.word_list_input.setPlaceholderText("Enter words to find, one per line:\n\nPYTHON\nPUZZLE\nSEARCH\n...")
        self.word_list_input.setFont(QFont("Consolas", 11))
        self.word_list_input.setMaximumHeight(140)
        right.addWidget(self.word_list_input)
        self.apply_words_btn = QPushButton("Apply Words & Start Timer")
        self.apply_words_btn.setStyleSheet("QPushButton{background:#4285f4;color:white;font-weight:bold;border-radius:6px;padding:8px}QPushButton:hover{background:#3367d6}")
        self.apply_words_btn.clicked.connect(self._on_apply_words)
        right.addWidget(self.apply_words_btn)
        grp_found = QGroupBox("Found Words")
        fl = QVBoxLayout(grp_found)
        self.found_list_widget = QListWidget()
        self.found_list_widget.setFont(QFont("Consolas", 11))
        self.found_list_widget.setStyleSheet("QListWidget{border:1px solid #dadce0;border-radius:4px}QListWidget::item{padding:3px 6px;border-radius:3px}")
        fl.addWidget(self.found_list_widget)
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("padding:4px")
        fl.addWidget(self.progress_label)
        right.addWidget(grp_found, 1)
        grp_stats = QGroupBox("Statistics")
        sl = QVBoxLayout(grp_stats)
        self.best_time_label = QLabel("Best Time: --:--")
        self.best_time_label.setFont(QFont("Consolas", 11))
        sl.addWidget(self.best_time_label)
        self.puzzles_solved_label = QLabel(f"Total Solved: {self._stats.get('puzzles_solved', 0)}")
        sl.addWidget(self.puzzles_solved_label)
        self.hints_label = QLabel("Hints: 0  Reveals: 0")
        self.hints_label.setStyleSheet("color:#ea4335; font-size:11px")
        sl.addWidget(self.hints_label)
        right.addWidget(grp_stats)
        instr = QLabel("Shortcuts:\n  H = Hint  |  Ctrl+R = Reveal\n  Ctrl+Z = Undo  |  Drag = Select")
        instr.setStyleSheet("color:#888; font-size:10px; padding:6px; background:#f8f9fa; border-radius:4px")
        instr.setWordWrap(True)
        right.addWidget(instr)

        right_w = QWidget(); right_w.setLayout(right); right_w.setFixedWidth(280)
        right_w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        splitter = QSplitter(Qt.Horizontal)
        grid_w = QWidget(); grid_w.setLayout(grid_layout)
        splitter.addWidget(grid_w); splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 0)
        outer = QHBoxLayout(self); outer.addWidget(splitter)

    def _tick(self):
        self._elapsed += 1
        m, s = self._elapsed // 60, self._elapsed % 60
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def load_puzzle(self, grid, words, size=None, placements=None):
        self.grid_widget.set_grid(grid, placements or [])
        self.grid_widget.set_word_set(words)
        self.word_list_input.setPlainText("\n".join(sorted(words)))
        self._update_found_display()
        self._elapsed = 0; self._hints_used = 0; self._reveals_used = 0
        self._timer.start()
        self.timer_label.setText("00:00")
        self._update_score(); self._update_progress()

    def _on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Puzzle", "", "Text Files (*.txt);;All Files (*)")
        if not path: return
        try:
            with open(path, "r") as f: content = f.read()
            try:
                data = json.loads(content)
                if "grid" in data and "words" in data:
                    self._load_wsp_data(data); return
            except (json.JSONDecodeError, KeyError):
                pass
            self._parse_puzzle_text(content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    def _on_load_wsp(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Puzzle", "", "Word Search Puzzle (*.wsp);;JSON Files (*.json);;All Files (*)")
        if not path: return
        try:
            self._load_wsp_data(json.loads(Path(path).read_text()))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load .wsp file:\n{e}")

    def _load_wsp_data(self, data):
        grid = data["grid"]
        words = data.get("words", [p["word"] for p in data.get("placements", [])])
        placements = data.get("placements", [])
        self.load_puzzle(grid, words, len(grid), placements)

    def _on_paste(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            QMessageBox.warning(self, "Empty", "Clipboard is empty."); return
        self._parse_puzzle_text(text)

    def _parse_puzzle_text(self, text):
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        if not lines:
            QMessageBox.warning(self, "Empty", "No content found."); return
        grid_lines = []; word_lines = []; in_grid = True
        for line in lines:
            cleaned = line.replace(" ", "").replace(",", "").replace("\t", "")
            if in_grid and cleaned.isalpha() and cleaned.isupper() and len(cleaned) > 1:
                grid_lines.append(cleaned)
            else:
                in_grid = False
                if cleaned: word_lines.append(cleaned)
        if not grid_lines:
            if all(len(l.replace(" ", "")) == 1 for l in lines if l.replace(" ", "")):
                chars = [l.strip() for l in lines if l.strip()]
                n = int(math.sqrt(len(chars)))
                if n * n == len(chars):
                    grid = [list(chars[r*n:(r+1)*n]) for r in range(n)]
                    self.grid_widget.set_grid(grid)
                    self.found_list_widget.clear(); self.progress_label.setText("0 / 0"); return
            QMessageBox.warning(self, "Parse Error", "Could not detect a grid in the text."); return
        n = len(grid_lines[0])
        for gl in grid_lines:
            if len(gl) != n:
                QMessageBox.warning(self, "Parse Error", f"Grid rows have different lengths ({len(gl)} vs {n})."); return
        grid = [list(gl) for gl in grid_lines]
        self.grid_widget.set_grid(grid)
        if word_lines:
            words = [w.strip().upper() for w in word_lines if w.strip()]
            self.grid_widget.set_word_set(words)
            self.word_list_input.setPlainText("\n".join(sorted(words)))
            self._update_found_display()
            self._elapsed = 0; self._hints_used = 0; self._reveals_used = 0
            self._timer.start(); self.timer_label.setText("00:00")

    def _on_apply_words(self):
        text = self.word_list_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Words", "Please enter words to find."); return
        if not self.grid_widget.grid:
            QMessageBox.warning(self, "No Grid", "Please load a puzzle grid first."); return
        words = [w.strip().upper() for w in text.splitlines() if w.strip()]
        self.grid_widget.set_word_set(words)
        self.grid_widget.found_words = set()
        self.grid_widget._color_map = {}
        self.grid_widget._player_map = {}
        self.grid_widget._color_idx_per_player = {0:0, 1:0, 2:0}
        self.grid_widget._undo_stack = []
        self._update_found_display(); self._update_progress()
        self._elapsed = 0; self._hints_used = 0; self._reveals_used = 0
        self._timer.start(); self.timer_label.setText("00:00")
        self._update_score(); self.grid_widget.update()

    def _on_selection_changed(self, text):
        if text:
            self.selection_label.setText(f"Selecting: {text}")
            self.selection_label.setStyleSheet("color:#202124;padding:4px 8px;min-height:28px;background:#fff9c4;border-radius:4px;font-weight:bold")
        else:
            self.selection_label.setText("")
            self.selection_label.setStyleSheet("color:#5f6368;padding:4px 8px;min-height:28px;background:#f1f3f4;border-radius:4px")

    def _on_word_found(self, word, player_id=0):
        self._snd.play("found")
        self._update_found_display(); self._update_progress(); self._update_score()
        self.timer_label.setStyleSheet("color:#34a853; padding:4px 12px; background:#e6f4ea; border-radius:6px")
        QTimer.singleShot(500, lambda: self.timer_label.setStyleSheet("color:#4285f4; padding:4px 12px; background:#e8f0fe; border-radius:6px"))

    def _on_all_found(self):
        self._timer.stop()
        self._snd.play("complete")
        m, s = self._elapsed // 60, self._elapsed % 60
        time_str = f"{m:02d}:{s:02d}"
        score = self._calculate_score()
        penalty = self._hints_used * 50 + self._reveals_used * 200
        final_score = max(0, score - penalty)
        self._stats["puzzles_solved"] = self._stats.get("puzzles_solved", 0) + 1
        self._stats["total_time"] = self._stats.get("total_time", 0) + self._elapsed
        key = f"{len(self.grid_widget.word_set)}_words"
        best = self._stats.get("best_times", {}).get(key)
        if best is None or self._elapsed < best:
            self._stats.setdefault("best_times", {})[key] = self._elapsed
            self.best_time_label.setText(f"Best Time: {time_str} (NEW!)")
            self.best_time_label.setStyleSheet("color:#34a853; font-weight:bold")
        else:
            bm, bs = best // 60, best % 60
            self.best_time_label.setText(f"Best Time: {bm:02d}:{bs:02d}")
        save_stats(self._stats)
        self.puzzles_solved_label.setText(f"Total Solved: {self._stats['puzzles_solved']}")
        details = f"Time: {time_str}\nBase Score: {score}\nHints: {self._hints_used} (-{self._hints_used*50})\nReveals: {self._reveals_used} (-{self._reveals_used*200})\nFinal Score: {final_score}"
        if self._hints_used == 0 and self._reveals_used == 0:
            details += "\n\nPerfect solve! No hints or reveals used!"
        QMessageBox.information(self, "Congratulations!", f"You found all words!\n\n{details}")

    def _on_pause_toggle(self, checked):
        self._paused = checked
        if checked:
            self._timer.stop()
            self.pause_btn.setText("Resume")
            self.timer_label.setStyleSheet("color:#fbbc05; padding:4px 12px; background:#fef7e0; border-radius:6px")
        else:
            self._timer.start()
            self.pause_btn.setText("Pause")
            self.timer_label.setStyleSheet("color:#4285f4; padding:4px 12px; background:#e8f0fe; border-radius:6px")

    def _on_miss(self):
        self._snd.play("miss")
        self.miss_label.setText("Miss!")
        QTimer.singleShot(400, lambda: self.miss_label.setText(""))

    def _on_hint(self):
        self._hints_used += 1
        self._snd.play("hint")
        self.grid_widget.show_hint_letter()
        self.hints_label.setText(f"Hints: {self._hints_used}  Reveals: {self._reveals_used}")

    def _on_reveal(self):
        self._reveals_used += 1
        self.grid_widget.reveal_word()
        self.hints_label.setText(f"Hints: {self._hints_used}  Reveals: {self._reveals_used}")

    def _on_auto_solve(self):
        self.grid_widget.auto_solve()

    def _on_reset(self):
        self.grid_widget.found_words = set()
        self.grid_widget._color_map = {}; self.grid_widget._player_map = {}
        self.grid_widget._color_idx_per_player = {0:0, 1:0, 2:0}
        self.grid_widget._undo_stack = []
        self._elapsed = 0; self._hints_used = 0; self._reveals_used = 0
        self._timer.stop(); self.timer_label.setText("00:00")
        self.timer_label.setStyleSheet("color:#4285f4; padding:4px 12px; background:#e8f0fe; border-radius:6px")
        self.hints_label.setText("Hints: 0  Reveals: 0")
        self._update_found_display(); self._update_progress(); self._update_score()
        self.grid_widget.update()

    def _calculate_score(self):
        total = len(self.grid_widget.word_set) if self.grid_widget.word_set else 1
        found = len(self.grid_widget.found_words)
        return found * 100 + max(0, 1000 - self._elapsed * 2)

    def _update_score(self):
        score = self._calculate_score()
        penalty = self._hints_used * 50 + self._reveals_used * 200
        self.score_label.setText(f"Score: {max(0, score - penalty)}")

    def _update_found_display(self):
        self.found_list_widget.clear()
        all_words = sorted(self.grid_widget.word_set) if self.grid_widget.word_set else []
        dir_symbols = {(0,1):"→",(1,0):"↓",(0,-1):"←",(-1,0):"↑",(1,1):"↘",(-1,-1):"↙",(1,-1):"↙",(-1,1):"↗"}
        # Show unfound words first, then found
        unfound_items = []
        found_items = []
        for w in all_words:
            if w in self.grid_widget.found_words:
                # Find direction for hint
                dir_hint = ""
                for p in self.grid_widget.placements:
                    if p["word"] == w:
                        dir_hint = " " + dir_symbols.get((p["dr"], p["dc"]), "")
                        break
                item = QListWidgetItem(f"✓ {w}{dir_hint}")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setForeground(QColor(52, 168, 83))
                found_items.append(item)
            else:
                item = QListWidgetItem(f"  {w}")
                item.setForeground(QColor(30, 30, 40))
                unfound_items.append(item)
        for item in unfound_items:
            self.found_list_widget.addItem(item)
        for item in found_items:
            self.found_list_widget.addItem(item)
        total = len(self.grid_widget.word_set) if self.grid_widget.word_set else 0
        self.progress_label.setText(f"{len(self.grid_widget.found_words)} / {total}")
        self.found_list_widget.scrollToBottom()

    def _update_progress(self):
        total = len(self.grid_widget.word_set) if self.grid_widget.word_set else 0
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(len(self.grid_widget.found_words))


# ---------------------------------------------------------------------------
# Multiplayer Tab  — 2-Player Local Multiplayer
# ---------------------------------------------------------------------------

class MultiplayerTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._current_player = 1
        self._player_names = {1: "Player 1", 2: "Player 2"}
        self._player_scores = {1: 0, 2: 0}
        self._player_words = {1: [], 2: []}
        self._game_active = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._elapsed = 0
        self._snd = get_sound_manager()

        # Round tracking state
        self._round_wins = {1: 0, 2: 0}
        self._current_round = 1
        self._best_of = 1  # 1 = single round, 3, 5, 7 for match play
        self._match_over = False
        self._saved_grid = None
        self._saved_placements = None
        self._saved_words = []

        # Pressure mode state
        self._pressure_mode = False
        self._turn_time_limit = 15  # seconds per turn
        self._turn_time_remaining = 0
        self._turn_timer = QTimer(self)
        self._turn_timer.setInterval(100)
        self._turn_timer.timeout.connect(self._turn_tick)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Top bar: game setup ---
        top_bar = QHBoxLayout()
        self.p1_name_input = QLineEdit("Player 1")
        self.p1_name_input.setFont(QFont("Arial", 11, QFont.Bold))
        self.p1_name_input.setMaximumWidth(140)
        self.p1_name_input.setStyleSheet("border:2px solid #4285f4; border-radius:6px; padding:4px 8px; color:#4285f4")
        self.p1_name_input.textChanged.connect(lambda t: self._set_player_name(1, t))
        top_bar.addWidget(self.p1_name_input)

        self.vs_label = QLabel("VS")
        self.vs_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.vs_label.setStyleSheet("color:#9e9e9e; padding:0 12px")
        top_bar.addWidget(self.vs_label)

        self.p2_name_input = QLineEdit("Player 2")
        self.p2_name_input.setFont(QFont("Arial", 11, QFont.Bold))
        self.p2_name_input.setMaximumWidth(140)
        self.p2_name_input.setStyleSheet("border:2px solid #ea4335; border-radius:6px; padding:4px 8px; color:#ea4335")
        self.p2_name_input.textChanged.connect(lambda t: self._set_player_name(2, t))
        top_bar.addWidget(self.p2_name_input)

        top_bar.addStretch()

        # Round tracking controls
        round_grp = QFrame()
        round_grp.setFrameShape(QFrame.Shape.StyledPanel)
        round_grp.setStyleSheet("QFrame{border:1px solid #dadce0; border-radius:6px; padding:4px}")
        rl = QHBoxLayout(round_grp)
        rl.setContentsMargins(6, 2, 6, 2)
        rl.addWidget(QLabel("Best of:"))
        self.best_of_combo = QComboBox()
        self.best_of_combo.addItems(["1", "3", "5", "7"])
        self.best_of_combo.setCurrentIndex(0)
        self.best_of_combo.setFixedWidth(56)
        self.best_of_combo.currentIndexChanged.connect(self._on_best_of_changed)
        rl.addWidget(self.best_of_combo)
        self.round_label = QLabel("R1")
        self.round_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.round_label.setStyleSheet("color:#5f6368; padding:2px 8px")
        rl.addWidget(self.round_label)
        self.round_score_label = QLabel("(0 - 0)")
        self.round_score_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.round_score_label.setStyleSheet("color:#fbbc05; padding:2px 8px")
        rl.addWidget(self.round_score_label)
        self.match_status_label = QLabel("")
        self.match_status_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.match_status_label.setStyleSheet("color:#34a853; padding:2px 8px")
        rl.addWidget(self.match_status_label)
        top_bar.addWidget(round_grp)

        top_bar.addStretch()

        self.turn_indicator = QLabel("Player 1's Turn")
        self.turn_indicator.setFont(QFont("Arial", 14, QFont.Bold))
        self.turn_indicator.setAlignment(Qt.AlignCenter)
        self.turn_indicator.setMinimumWidth(200)
        self.turn_indicator.setStyleSheet(
            "color:white; padding:8px 16px; background:#4285f4; border-radius:8px"
        )
        top_bar.addWidget(self.turn_indicator)

        top_bar.addStretch()
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.timer_label.setStyleSheet("color:#5f6368; padding:4px 12px; background:#f1f3f4; border-radius:6px")
        top_bar.addWidget(self.timer_label)
        main_layout.addLayout(top_bar)

        # --- Pressure mode bar ---
        pressure_bar = QHBoxLayout()
        self.pressure_checkbox = QCheckBox("Pressure Mode")
        self.pressure_checkbox.setFont(QFont("Arial", 11, QFont.Bold))
        self.pressure_checkbox.setStyleSheet("color:#ea4335; padding:2px")
        self.pressure_checkbox.toggled.connect(self._on_pressure_toggled)
        pressure_bar.addWidget(self.pressure_checkbox)
        pressure_bar.addWidget(QLabel("Turn Timer:"))
        self.turn_time_spin = QSpinBox()
        self.turn_time_spin.setRange(5, 120)
        self.turn_time_spin.setValue(15)
        self.turn_time_spin.setSuffix("s")
        self.turn_time_spin.setSingleStep(5)
        self.turn_time_spin.setFixedWidth(80)
        self.turn_time_spin.valueChanged.connect(self._on_turn_time_changed)
        pressure_bar.addWidget(self.turn_time_spin)
        self.turn_timer_label = QLabel("")
        self.turn_timer_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.turn_timer_label.setAlignment(Qt.AlignCenter)
        self.turn_timer_label.setMinimumWidth(80)
        self.turn_timer_label.setStyleSheet("color:#34a853; padding:2px 12px; background:#e6f4ea; border-radius:8px")
        pressure_bar.addWidget(self.turn_timer_label)
        self.turn_progress = QProgressBar()
        self.turn_progress.setRange(0, 100)
        self.turn_progress.setValue(100)
        self.turn_progress.setTextVisible(False)
        self.turn_progress.setFixedHeight(10)
        self.turn_progress.setMaximumWidth(200)
        self.turn_progress.setStyleSheet(
            "QProgressBar{border:1px solid #dadce0;border-radius:5px;background:#e8f0fe}"
            "QProgressBar::chunk{background:#34a853;border-radius:4px}"
        )
        pressure_bar.addWidget(self.turn_progress)
        pressure_bar.addStretch()
        main_layout.addLayout(pressure_bar)

        # --- Score bar ---
        score_bar = QHBoxLayout()
        self.p1_score_label = QLabel("0 words")
        self.p1_score_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.p1_score_label.setStyleSheet("color:#4285f4; padding:6px 16px; background:#e8f0fe; border-radius:6px; border:2px solid #4285f4")
        self.p1_score_label.setAlignment(Qt.AlignCenter)
        score_bar.addWidget(self.p1_score_label)

        # Progress bar (shared)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m  (%p%)")
        self.progress_bar.setStyleSheet(
            "QProgressBar{border:1px solid #dadce0;border-radius:6px;text-align:center;height:28px}"
            "QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4285f4,stop:1 #ea4335);border-radius:5px}"
        )
        score_bar.addWidget(self.progress_bar, 1)

        self.p2_score_label = QLabel("0 words")
        self.p2_score_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.p2_score_label.setStyleSheet("color:#ea4335; padding:6px 16px; background:#fce8e6; border-radius:6px; border:2px solid #ea4335")
        self.p2_score_label.setAlignment(Qt.AlignCenter)
        score_bar.addWidget(self.p2_score_label)
        main_layout.addLayout(score_bar)

        # --- Selection preview ---
        self.selection_label = QLabel("")
        self.selection_label.setFont(QFont("Consolas", 13, QFont.Bold))
        self.selection_label.setStyleSheet("color:#5f6368; padding:4px 8px; min-height:28px; background:#f1f3f4; border-radius:4px")
        self.selection_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.selection_label)

        # --- Grid ---
        self.grid_widget = GridWidget(interactive=True)
        self.grid_widget.wordFound.connect(self._on_word_found_mp)
        self.grid_widget.allFound.connect(self._on_all_found_mp)
        self.grid_widget.selectionChanged.connect(self._on_selection_changed)
        self.grid_widget.missSelection.connect(lambda: self._snd.play("miss"))
        main_layout.addWidget(self.grid_widget, 1)

        # --- Bottom controls ---
        ctrl = QHBoxLayout()
        self.load_btn = QPushButton("Load Puzzle (.wsp)")
        self.load_btn.clicked.connect(self._on_load)
        ctrl.addWidget(self.load_btn)

        self.paste_btn = QPushButton("Paste Grid")
        self.paste_btn.clicked.connect(self._on_paste)
        ctrl.addWidget(self.paste_btn)

        self.words_input = QLineEdit()
        self.words_input.setPlaceholderText("Or paste words here, comma-separated, then click Load Words")
        self.words_input.setFont(QFont("Consolas", 10))
        ctrl.addWidget(self.words_input, 1)

        self.load_words_btn = QPushButton("Load Words")
        self.load_words_btn.setStyleSheet("QPushButton{background:#4285f4;color:white;font-weight:bold;border-radius:6px;padding:6px}QPushButton:hover{background:#3367d6}")
        self.load_words_btn.clicked.connect(self._on_load_words_from_input)
        ctrl.addWidget(self.load_words_btn)
        main_layout.addLayout(ctrl)

        # Word list display and reset
        ctrl2 = QHBoxLayout()
        self.word_list_display = QLabel("")
        self.word_list_display.setFont(QFont("Consolas", 10))
        self.word_list_display.setStyleSheet("padding:4px; background:#f8f9fa; border-radius:4px")
        self.word_list_display.setWordWrap(True)
        self.word_list_display.setAlignment(Qt.AlignCenter)
        ctrl2.addWidget(self.word_list_display, 1)

        self.next_round_btn = QPushButton("Next Round")
        self.next_round_btn.setEnabled(False)
        self.next_round_btn.setStyleSheet("QPushButton{background:#fbbc05;color:#3c4043;font-weight:bold;font-size:12px;border-radius:6px;padding:6px 12px}QPushButton:hover{background:#f0b400}")
        self.next_round_btn.clicked.connect(self._on_next_round)
        ctrl2.addWidget(self.next_round_btn)

        self.reset_btn = QPushButton("New Match")
        self.reset_btn.setStyleSheet("QPushButton{background:#f1f3f4;border-radius:6px;padding:6px}QPushButton:hover{background:#d2d5d9}")
        self.reset_btn.clicked.connect(self._on_reset)
        ctrl2.addWidget(self.reset_btn)
        ctrl2.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(120)
        self.zoom_slider.valueChanged.connect(lambda v: self.grid_widget.set_zoom(v / 100.0))
        ctrl2.addWidget(self.zoom_slider)
        main_layout.addLayout(ctrl2)

    def _set_player_name(self, player, name):
        self._player_names[player] = name.strip() or f"Player {player}"

    def _on_best_of_changed(self, index):
        values = [1, 3, 5, 7]
        self._best_of = values[index]
        self._update_round_display()

    def _on_pressure_toggled(self, checked):
        self._pressure_mode = checked
        self.turn_time_spin.setEnabled(checked)
        if checked and self._game_active:
            self._start_turn_timer()
        elif not checked:
            self._stop_turn_timer()
            self.turn_timer_label.setText("")
            self.turn_progress.setValue(100)
            self.turn_progress.setStyleSheet(
                "QProgressBar{border:1px solid #dadce0;border-radius:5px;background:#e8f0fe}"
                "QProgressBar::chunk{background:#34a853;border-radius:4px}"
            )

    def _on_turn_time_changed(self, val):
        self._turn_time_limit = val
        if self._pressure_mode and self._game_active:
            self._start_turn_timer()

    def _update_round_display(self):
        wins_needed = (self._best_of + 1) // 2
        r1, r2 = self._round_wins[1], self._round_wins[2]
        if self._best_of > 1:
            self.round_label.setText(f"R{self._current_round}")
            self.round_score_label.setText(f"({r1} - {r2})")
            # Dot indicators for round wins
            p1_dots = "\u25cf " * r1 + "\u25cb " * (wins_needed - r1)
            p2_dots = "\u25cf " * r2 + "\u25cb " * (wins_needed - r2)
            self.p1_score_label.setText(f"{self._player_names[1]}: {p1_dots.strip()}")
            self.p2_score_label.setText(f"{self._player_names[2]}: {p2_dots.strip()}")
        else:
            self.round_label.setText("")
            self.round_score_label.setText("")
            self._update_word_score_labels()

    def _update_word_score_labels(self):
        p1_count = len(self.grid_widget.get_player_words(1))
        p2_count = len(self.grid_widget.get_player_words(2))
        self.p1_score_label.setText(f"{self._player_names[1]}: {p1_count}")
        self.p2_score_label.setText(f"{self._player_names[2]}: {p2_count}")

    def _update_turn_indicator(self):
        if self._match_over:
            return
        if self._current_player == 1:
            color = "#4285f4"
            name = self._player_names[1]
        else:
            color = "#ea4335"
            name = self._player_names[2]
        round_text = f" (R{self._current_round})" if self._best_of > 1 else ""
        self.turn_indicator.setText(f"{name}'s Turn{round_text}")
        self.turn_indicator.setStyleSheet(
            f"color:white; padding:8px 16px; background:{color}; border-radius:8px"
        )

    def _update_scores(self):
        if self._best_of > 1:
            self._update_round_display()
        else:
            self._update_word_score_labels()
        # Update progress
        total = len(self.grid_widget.word_set) if self.grid_widget.word_set else 0
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(len(self.grid_widget.found_words))

    def _tick(self):
        self._elapsed += 1
        m, s = self._elapsed // 60, self._elapsed % 60
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    # --- Pressure mode turn timer ---

    def _start_turn_timer(self):
        self._turn_time_remaining = self._turn_time_limit * 10  # tenths of a second
        self._turn_timer.start()
        self._update_turn_timer_display()

    def _stop_turn_timer(self):
        self._turn_timer.stop()

    def _turn_tick(self):
        self._turn_time_remaining -= 1
        if self._turn_time_remaining <= 0:
            self._turn_time_remaining = 0
            self._update_turn_timer_display()
            self._on_turn_timeout()
            return
        self._update_turn_timer_display()
        # Play tick sound in last 3 seconds
        if self._turn_time_remaining <= 30 and self._turn_time_remaining % 10 == 0:
            self._snd.play("tick")

    def _update_turn_timer_display(self):
        if not self._pressure_mode:
            return
        tenths = self._turn_time_remaining
        seconds = tenths / 10.0
        self.turn_timer_label.setText(f"{seconds:.1f}s")
        pct = (tenths / (self._turn_time_limit * 10)) * 100
        self.turn_progress.setValue(int(pct))
        if seconds > self._turn_time_limit * 0.5:
            color = "#34a853"
            bg = "#e6f4ea"
            chunk = "#34a853"
        elif seconds > self._turn_time_limit * 0.25:
            color = "#fbbc05"
            bg = "#fef7e0"
            chunk = "#fbbc05"
        else:
            color = "#ea4335"
            bg = "#fce8e6"
            chunk = "#ea4335"
        self.turn_timer_label.setStyleSheet(f"color:{color}; padding:2px 12px; background:{bg}; border-radius:8px")
        self.turn_progress.setStyleSheet(
            f"QProgressBar{{border:1px solid #dadce0;border-radius:5px;background:#e8f0fe}}"
            f"QProgressBar::chunk{{background:{chunk};border-radius:4px}}"
        )

    def _on_turn_timeout(self):
        """Turn timer expired — skip to other player."""
        self._stop_turn_timer()
        if not self._game_active:
            return
        self._snd.play("buzzer")
        name = self._player_names[self._current_player]
        self.turn_indicator.setText(f"{name} timed out!")
        self.turn_indicator.setStyleSheet("color:white; padding:8px 16px; background:#ea4335; border-radius:8px")
        QTimer.singleShot(800, self._switch_turn)

    def _switch_turn(self):
        if not self._game_active:
            return
        self._current_player = 2 if self._current_player == 1 else 1
        self.grid_widget.set_current_player(self._current_player)
        self._update_turn_indicator()
        if self._pressure_mode:
            self._start_turn_timer()

    def load_puzzle(self, grid, words, placements=None):
        self._saved_grid = [row[:] for row in grid]
        self._saved_placements = [p.copy() for p in (placements or [])]
        self._saved_words = list(words)
        self._load_round(grid, words, placements)

    def _load_round(self, grid, words, placements=None):
        self.grid_widget.set_grid(grid, placements or [])
        self.grid_widget.set_word_set(words)
        self._current_player = 1
        self.grid_widget.set_current_player(1)
        self._game_active = True
        self._elapsed = 0
        self._timer.start()
        self.timer_label.setText("00:00")
        self._update_turn_indicator()
        self._update_scores()
        self.word_list_display.setText("Words: " + ", ".join(sorted(words)))
        self.next_round_btn.setEnabled(False)
        self.match_status_label.setText("")
        self.best_of_combo.setEnabled(False)
        if self._pressure_mode:
            self._start_turn_timer()

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Puzzle", "", "Word Search Puzzle (*.wsp);;JSON Files (*.json);;Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            content = Path(path).read_text()
            try:
                data = json.loads(content)
                if "grid" in data and "words" in data:
                    self.load_puzzle(data["grid"], data["words"], data.get("placements", []))
                    return
            except (json.JSONDecodeError, KeyError):
                pass
            # Try as text grid
            lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
            grid_lines = []
            for line in lines:
                cleaned = line.replace(" ", "").replace(",", "").replace("\t", "")
                if cleaned.isalpha() and cleaned.isupper() and len(cleaned) > 1:
                    grid_lines.append(cleaned)
            if grid_lines:
                n = len(grid_lines[0])
                grid = [list(gl) for gl in grid_lines]
                self.grid_widget.set_grid(grid)
                self._current_player = 1
                self.grid_widget.set_current_player(1)
                self._game_active = False
                self._update_turn_indicator()
                self.word_list_display.setText(f"Grid loaded ({n}x{n}). Enter words and click Load Words.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

    def _on_paste(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            QMessageBox.warning(self, "Empty", "Clipboard is empty."); return
        # Try JSON first
        try:
            data = json.loads(text)
            if "grid" in data and "words" in data:
                self.load_puzzle(data["grid"], data["words"], data.get("placements", []))
                return
        except (json.JSONDecodeError, KeyError):
            pass
        self.words_input.setText(text.replace("\n", ", "))

    def _on_load_words_from_input(self):
        if not self.grid_widget.grid:
            QMessageBox.warning(self, "No Grid", "Load a puzzle grid first!"); return
        text = self.words_input.text().strip()
        if not text:
            QMessageBox.warning(self, "No Words", "Enter words!"); return
        # Parse: comma, space, or newline separated
        words = [w.strip().upper() for w in text.replace(",", "\n").splitlines() if w.strip()]
        self.load_puzzle(self.grid_widget.grid, words, self.grid_widget.placements)

    def _on_word_found_mp(self, word, player_id):
        """Called when a word is found by the current player."""
        if not self._game_active:
            return
        who = self._current_player
        # Play sound
        self._snd.play("found_p2" if who == 2 else "found")

        # Stop pressure timer, switch turns, restart
        self._stop_turn_timer()
        self._current_player = 2 if self._current_player == 1 else 1
        self.grid_widget.set_current_player(self._current_player)
        self._snd.play("turn")

        self._update_turn_indicator()
        self._update_scores()

        # Restart turn timer for the new player
        if self._pressure_mode and self._game_active:
            self._start_turn_timer()

    def _on_all_found_mp(self):
        """All words found — determine round winner, update match state."""
        self._timer.stop()
        self._stop_turn_timer()
        m, s = self._elapsed // 60, self._elapsed % 60
        p1_words = self.grid_widget.get_player_words(1)
        p2_words = self.grid_widget.get_player_words(2)
        p1_letter_score = sum(len(w) for w in p1_words)
        p2_letter_score = sum(len(w) for w in p2_words)
        n1, n2 = self._player_names[1], self._player_names[2]

        # Determine round winner
        round_winner = None
        detail = ""
        if len(p1_words) > len(p2_words):
            round_winner = 1
            detail = f"{n1} found {len(p1_words)} words vs {n2}'s {len(p2_words)}"
        elif len(p2_words) > len(p1_words):
            round_winner = 2
            detail = f"{n2} found {len(p2_words)} words vs {n1}'s {len(p1_words)}"
        elif p1_letter_score > p2_letter_score:
            round_winner = 1
            detail = f"Tied on count ({len(p1_words)}), but {n1} found longer words ({p1_letter_score} vs {p2_letter_score} letters)"
        elif p2_letter_score > p1_letter_score:
            round_winner = 2
            detail = f"Tied on count ({len(p1_words)}), but {n2} found longer words ({p2_letter_score} vs {p1_letter_score} letters)"
        else:
            detail = f"Perfect tie! Both found {len(p1_words)} words with {p1_letter_score} total letters"

        self._game_active = False

        # --- Single round mode (no match tracking) ---
        if self._best_of <= 1:
            self._snd.play("victory")
            result = f"Time: {m:02d}:{s:02d}\n\n{detail}"
            if round_winner:
                winner_name = self._player_names[round_winner]
                result += f"\n\n{winner_name} WINS!"
                self.turn_indicator.setText(f"{winner_name} Wins!")
                color = "#4285f4" if round_winner == 1 else "#ea4335"
                self.turn_indicator.setStyleSheet(f"color:white; padding:8px 16px; background:{color}; border-radius:8px; font-size:16px")
            else:
                result += "\n\nIt's a TIE!"
                self.turn_indicator.setText("It's a TIE!")
                self.turn_indicator.setStyleSheet("color:white; padding:8px 16px; background:#9c27b0; border-radius:8px; font-size:16px")
            QMessageBox.information(self, "Game Over!", result)
            return

        # --- Match play mode (best of 3/5/7) ---
        if round_winner:
            self._round_wins[round_winner] += 1
            self._snd.play("round_win")
        wins_needed = (self._best_of + 1) // 2
        self._update_round_display()

        result = f"Round {self._current_round} Result\nTime: {m:02d}:{s:02d}\n\n{detail}"
        if round_winner:
            winner_name = self._player_names[round_winner]
            result += f"\n\nRound Winner: {winner_name}"
        else:
            result += "\n\nRound Draw!"

        # Check if match is decided
        match_winner = None
        for pid in (1, 2):
            if self._round_wins[pid] >= wins_needed:
                match_winner = pid
                break

        if match_winner:
            self._match_over = True
            mw_name = self._player_names[match_winner]
            r1, r2 = self._round_wins[1], self._round_wins[2]
            result += f"\n\n{'='*30}"
            result += f"\nMATCH OVER!"
            result += f"\nFinal Score: {n1} {r1} - {r2} {n2}"
            result += f"\n\n{mw_name} WINS THE MATCH!"
            self._snd.play("match_win")
            self.turn_indicator.setText(f"{mw_name} Wins Match!")
            color = "#4285f4" if match_winner == 1 else "#ea4335"
            self.turn_indicator.setStyleSheet(f"color:white; padding:8px 16px; background:{color}; border-radius:8px; font-size:16px")
            self.match_status_label.setText("MATCH OVER")
            self.match_status_label.setStyleSheet(f"color:{color}; padding:2px 8px; font-weight:bold")
            self.best_of_combo.setEnabled(True)
            QMessageBox.information(self, "Match Over!", result)
        else:
            # Match continues — enable next round
            remaining = wins_needed - max(self._round_wins[1], self._round_wins[2])
            rounds_left = self._best_of - self._current_round
            self.match_status_label.setText(f"Next: R{self._current_round + 1}")
            self.match_status_label.setStyleSheet("color:#fbbc05; padding:2px 8px; font-weight:bold")
            self.next_round_btn.setEnabled(True)
            result += f"\n\nMatch Score: {n1} {self._round_wins[1]} - {self._round_wins[2]} {n2}"
            result += f"\n(First to {wins_needed} wins)"
            QMessageBox.information(self, f"Round {self._current_round} Complete", result)

    def _on_next_round(self):
        """Start the next round in a match. Re-uses the same puzzle grid."""
        if self._match_over:
            return
        self._current_round += 1
        wins_needed = (self._best_of + 1) // 2
        if self._current_round > self._best_of:
            # Shouldn't happen, but safety check
            return
        if self._saved_grid:
            self._load_round(self._saved_grid, self._saved_words, self._saved_placements)
        else:
            # Fallback: just reset current grid
            grid = self.grid_widget.grid
            words = sorted(self.grid_widget.word_set)
            placements = self.grid_widget.placements
            self._load_round(grid, words, placements)

    def _on_selection_changed(self, text):
        if text:
            name = self._player_names.get(self._current_player, "?")
            self.selection_label.setText(f"[{name}] {text}")
            if self._current_player == 1:
                self.selection_label.setStyleSheet("color:#4285f4;padding:4px 8px;min-height:28px;background:#e8f0fe;border-radius:4px;font-weight:bold")
            else:
                self.selection_label.setStyleSheet("color:#ea4335;padding:4px 8px;min-height:28px;background:#fce8e6;border-radius:4px;font-weight:bold")
        else:
            self.selection_label.setText("")
            self.selection_label.setStyleSheet("color:#5f6368;padding:4px 8px;min-height:28px;background:#f1f3f4;border-radius:4px")

    def _on_reset(self):
        self.grid_widget.found_words = set()
        self.grid_widget._color_map = {}
        self.grid_widget._player_map = {}
        self.grid_widget._color_idx_per_player = {0:0, 1:0, 2:0}
        self.grid_widget._undo_stack = []
        self._current_player = 1
        self.grid_widget.set_current_player(1)
        self._game_active = False
        self._elapsed = 0
        self._timer.stop()
        self._stop_turn_timer()
        self.timer_label.setText("00:00")
        # Reset match state
        self._round_wins = {1: 0, 2: 0}
        self._current_round = 1
        self._match_over = False
        self._saved_grid = None
        self._saved_placements = None
        self._saved_words = []
        self._update_turn_indicator()
        self._update_round_display()
        self._update_scores()
        self.word_list_display.setText("")
        self.selection_label.setText("")
        self.turn_timer_label.setText("")
        self.turn_progress.setValue(100)
        self.next_round_btn.setEnabled(False)
        self.match_status_label.setText("")
        self.best_of_combo.setEnabled(True)
        self.grid_widget.update()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Word Search Puzzle — Maker, Solver & Multiplayer")
        self.resize(1200, 820)
        self._dark_mode = False
        self._snd = get_sound_manager()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 12))
        self.maker_tab = MakerTab()
        self.solver_tab = SolverTab()
        self.multiplayer_tab = MultiplayerTab()
        self.tabs.addTab(self.maker_tab, "  Maker  ")
        self.tabs.addTab(self.solver_tab, "  Solver  ")
        self.tabs.addTab(self.multiplayer_tab, "  Multiplayer  ")
        layout.addWidget(self.tabs, 1)

        self.maker_tab.send_to_solver_btn.clicked.connect(self._send_to_solver)
        self.maker_tab.send_to_multi_btn.clicked.connect(self._send_to_multiplayer)

        self._build_menu()
        self._build_toolbar()
        self.statusBar().showMessage("Ready — Pick a difficulty or enter your own words!")
        self._apply_light_style()

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(24, 24))
        self.addToolBar(tb)
        tb.addAction(self._new_action)
        tb.addSeparator()
        self.dark_mode_action = QAction("Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setShortcut(QKeySequence("Ctrl+D"))
        self.dark_mode_action.triggered.connect(self._toggle_dark_mode)
        tb.addAction(self.dark_mode_action)
        self.mute_action = QAction("Mute Sounds", self)
        self.mute_action.setCheckable(True)
        self.mute_action.setShortcut(QKeySequence("Ctrl+M"))
        self.mute_action.triggered.connect(self._toggle_mute)
        tb.addAction(self.mute_action)
        tb.addSeparator()
        tb.addAction(self._export_action)
        tb.addAction(self._save_action)
        tb.addSeparator()
        tb.addAction(self._about_action)

    def _build_menu(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("File")
        self._new_action = QAction("New Puzzle", self)
        self._new_action.setShortcut(QKeySequence.StandardKey.New)
        self._new_action.triggered.connect(self._new_puzzle)
        file_menu.addAction(self._new_action)
        self._export_action = QAction("Export PDF...", self)
        self._export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._export_action.triggered.connect(self.maker_tab._on_export_pdf)
        file_menu.addAction(self._export_action)
        self._save_action = QAction("Save Puzzle (.wsp)...", self)
        self._save_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_action.triggered.connect(self.maker_tab._on_save)
        file_menu.addAction(self._save_action)
        file_menu.addSeparator()
        load_action = QAction("Open Puzzle (.wsp)...", self)
        load_action.setShortcut(QKeySequence.StandardKey.Open)
        load_action.triggered.connect(self.solver_tab._on_load_wsp)
        file_menu.addAction(load_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = mb.addMenu("View")
        zoom_in = QAction("Zoom In", self)
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in.triggered.connect(lambda: self._zoom(10))
        view_menu.addAction(zoom_in)
        zoom_out = QAction("Zoom Out", self)
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out.triggered.connect(lambda: self._zoom(-10))
        view_menu.addAction(zoom_out)
        zoom_reset = QAction("Reset Zoom", self)
        zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset.triggered.connect(lambda: self._set_zoom(100))
        view_menu.addAction(zoom_reset)

        sound_menu = mb.addMenu("Sound")
        self._mute_menu_action = QAction("Mute / Unmute", self)
        self._mute_menu_action.setShortcut(QKeySequence("Ctrl+M"))
        self._mute_menu_action.triggered.connect(self._toggle_mute)
        sound_menu.addAction(self._mute_menu_action)
        test_sound = QAction("Test Sound", self)
        test_sound.triggered.connect(lambda: self._snd.play("found"))
        sound_menu.addAction(test_sound)

        help_menu = mb.addMenu("Help")
        self._about_action = QAction("About", self)
        self._about_action.triggered.connect(self._show_about)
        help_menu.addAction(self._about_action)
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

    def _zoom(self, delta):
        for tab in (self.solver_tab, self.multiplayer_tab):
            if hasattr(tab, 'zoom_slider'):
                tab.zoom_slider.setValue(min(300, max(50, tab.zoom_slider.value() + delta)))

    def _set_zoom(self, val):
        for tab in (self.solver_tab, self.multiplayer_tab):
            if hasattr(tab, 'zoom_slider'):
                tab.zoom_slider.setValue(val)

    def _toggle_dark_mode(self, checked):
        self._dark_mode = checked
        if checked:
            self._apply_dark_style()
        else:
            self._apply_light_style()
        # Propagate dark mode to all grid widgets
        for tab in (self.maker_tab, self.solver_tab, self.multiplayer_tab):
            if hasattr(tab, 'grid_widget'):
                tab.grid_widget.set_dark_mode(checked)

    def _toggle_mute(self, checked=None):
        self._snd.muted = not self._snd.muted
        self.mute_action.setChecked(self._snd.muted)
        self._mute_menu_action.setChecked(self._snd.muted)
        state = "muted" if self._snd.muted else "unmuted"
        self.statusBar().showMessage(f"Sound {state}", 2000)

    def _apply_light_style(self):
        self.setStyleSheet("""
            QMainWindow{background:#ffffff}
            QTabWidget::pane{border:1px solid #dadce0;border-radius:8px}
            QTabBar::tab{background:#f1f3f4;padding:10px 24px;margin-right:2px;border-top-left-radius:6px;border-top-right-radius:6px;font-weight:bold;font-size:13px;color:#5f6368}
            QTabBar::tab:selected{background:#ffffff;border-bottom:2px solid #4285f4;color:#4285f4}
            QTabBar::tab:hover{background:#e8eaed}
            QGroupBox{font-weight:bold;font-size:12px;border:1px solid #dadce0;border-radius:6px;margin-top:10px;padding-top:16px;color:#202124}
            QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px}
            QTextEdit{border:1px solid #dadce0;border-radius:4px;padding:6px;background:#ffffff;color:#202124}
            QSpinBox,QComboBox,QLineEdit{border:1px solid #dadce0;border-radius:4px;padding:4px 8px;background:#ffffff;color:#202124}
            QLabel{color:#202124}
            QStatusBar{background:#f8f9fa;color:#5f6368}
            QToolBar{background:#ffffff;border-bottom:1px solid #e0e0e0;spacing:4px}
            QMenuBar{background:#ffffff;color:#202124}
            QMenuBar::item:selected{background:#e8f0fe;border-radius:4px}
            QMenu{background:#ffffff;color:#202124;border:1px solid #dadce0}
            QMenu::item:selected{background:#e8f0fe}
            QPushButton{color:#202124}
            QSlider::groove:horizontal{height:6px;background:#dadce0;border-radius:3px}
            QSlider::handle:horizontal{width:16px;height:16px;margin:-5px 0;background:#4285f4;border-radius:8px}
        """)

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QMainWindow{background:#1e1e2e}
            QTabWidget::pane{border:1px solid #45475a;border-radius:8px}
            QTabBar::tab{background:#313244;padding:10px 24px;margin-right:2px;border-top-left-radius:6px;border-top-right-radius:6px;font-weight:bold;font-size:13px;color:#a6adc8}
            QTabBar::tab:selected{background:#1e1e2e;border-bottom:2px solid #89b4fa;color:#89b4fa}
            QTabBar::tab:hover{background:#45475a}
            QGroupBox{font-weight:bold;font-size:12px;border:1px solid #45475a;border-radius:6px;margin-top:10px;padding-top:16px;color:#cdd6f4}
            QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px}
            QTextEdit{border:1px solid #45475a;border-radius:4px;padding:6px;background:#313244;color:#cdd6f4}
            QSpinBox,QComboBox,QLineEdit{border:1px solid #45475a;border-radius:4px;padding:4px 8px;background:#313244;color:#cdd6f4}
            QLabel{color:#cdd6f4}
            QStatusBar{background:#181825;color:#a6adc8}
            QToolBar{background:#1e1e2e;border-bottom:1px solid #45475a;spacing:4px}
            QMenuBar{background:#1e1e2e;color:#cdd6f4}
            QMenuBar::item:selected{background:#45475a;border-radius:4px}
            QMenu{background:#313244;color:#cdd6f4;border:1px solid #45475a}
            QMenu::item:selected{background:#45475a}
            QPushButton{color:#cdd6f4}
            QSlider::groove:horizontal{height:6px;background:#45475a;border-radius:3px}
            QSlider::handle:horizontal{width:16px;height:16px;margin:-5px 0;background:#89b4fa;border-radius:8px}
            QListWidget{background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:4px}
            QProgressBar{border:1px solid #45475a;border-radius:6px;text-align:center;height:22px;background:#313244;color:#cdd6f4}
            QProgressBar::chunk{background:#89b4fa;border-radius:5px}
        """)

    def _new_puzzle(self):
        self.maker_tab._on_clear()
        self.solver_tab._on_reset()
        self.multiplayer_tab._on_reset()
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage("Ready — Pick a difficulty or enter your own words!")

    def _send_to_solver(self):
        grid, words, size, placements = self.maker_tab.get_puzzle_data()
        if not grid: return
        self.solver_tab.load_puzzle(grid, words, size, placements)
        self.tabs.setCurrentIndex(1)
        self.statusBar().showMessage(f"Puzzle loaded in Solver tab — {len(words)} words to find!")

    def _send_to_multiplayer(self):
        grid, words, size, placements = self.maker_tab.get_puzzle_data()
        if not grid: return
        self.multiplayer_tab.load_puzzle(grid, words, placements)
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage(f"Multiplayer started — {len(words)} words! {self.multiplayer_tab._player_names[1]} goes first!")

    def _show_about(self):
        QMessageBox.about(self, "About Word Search Puzzle",
            "<h3>Word Search Puzzle — Maker, Solver & Multiplayer</h3>"
            "<p>Create and solve word search puzzles, or compete with a friend!</p>"
            "<p><b>Maker:</b> Pick a difficulty, choose a theme, generate & export. "
            "Regenerate for a fresh layout with the same words.</p>"
            "<p><b>Solver:</b> Load a puzzle, click & drag to find words. "
            "Green highlight = valid word! Pause timer anytime.</p>"
            "<p><b>Multiplayer:</b> Two players take turns. Best of 3/5/7 matches. "
            "Pressure mode with per-turn countdown.</p>"
            "<p><b>Grid:</b> Coordinate labels (A-Z, 1-N), dark mode support, "
            "smart retry for better word placement.</p>"
            "<hr><p>Built with PySide6 | Procedural audio | "
            "Save custom word lists as .wl files</p>")

    def _show_shortcuts(self):
        QMessageBox.information(self, "Keyboard Shortcuts",
            "<h3>Keyboard Shortcuts</h3><table cellpadding='6'>"
            "<tr><td><b>Ctrl+N</b></td><td>New puzzle</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save puzzle (.wsp)</td></tr>"
            "<tr><td><b>Ctrl+Shift+S</b></td><td>Export PDF</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Open puzzle (.wsp)</td></tr>"
            "<tr><td><b>Ctrl+D</b></td><td>Toggle dark mode</td></tr>"
            "<tr><td><b>Ctrl+M</b></td><td>Mute / unmute sounds</td></tr>"
            "<tr><td><b>Ctrl++/-</b></td><td>Zoom in/out</td></tr>"
            "<tr><td><b>Ctrl+0</b></td><td>Reset zoom</td></tr>"
            "<tr><td><b>H</b></td><td>Show hint (flash first letter)</td></tr>"
            "<tr><td><b>Ctrl+R</b></td><td>Reveal a word</td></tr>"
            "<tr><td><b>Ctrl+Z</b></td><td>Undo last found word</td></tr>"
            "</table>")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Word Search Puzzle")
    app.setOrganizationName("WordSearch")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()