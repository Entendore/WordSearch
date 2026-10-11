import sys
import random
import string
import requests
import textwrap
from io import BytesIO

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QPlainTextEdit, QMessageBox, QFileDialog,
    QSpinBox, QFormLayout, QProgressBar, QGroupBox, QCheckBox, QLineEdit
)
from PySide6.QtCore import QThread, Signal
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips
import numpy as np

# --- APIs & Logic ---

def get_definition(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data[0]['meanings'][0]['definitions'][0]['definition']
    except Exception:
        pass
    return "Definition not found."

def get_wikipedia_image(word):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{word}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'thumbnail' in data and data['thumbnail'].get('source'):
                img_url = data['thumbnail']['source']
                img_data = requests.get(img_url, timeout=5).content
                return Image.open(BytesIO(img_data)).convert("RGBA")
    except Exception:
        pass
    return None

def generate_word_search(words, size=12):
    grid = [[None for _ in range(size)] for _ in range(size)]
    directions = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]
    word_coords = {}

    for word in words:
        word = word.upper()
        placed = False
        attempts = 0
        while not placed and attempts < 200:
            attempts += 1
            dr, dc = random.choice(directions)
            r = random.randint(0, size - 1)
            c = random.randint(0, size - 1)

            fits = True
            coords = []
            for i in range(len(word)):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < size and 0 <= nc < size:
                    if grid[nr][nc] is not None and grid[nr][nc] != word[i]:
                        fits = False
                        break
                    coords.append((nr, nc))
                else:
                    fits = False
                    break
            
            if fits:
                for i, (nr, nc) in enumerate(coords):
                    grid[nr][nc] = word[i]
                word_coords[word] = coords
                placed = True

    for r in range(size):
        for c in range(size):
            if grid[r][c] is None:
                grid[r][c] = random.choice(string.ascii_uppercase)

    return grid, word_coords

# --- Video Generation Thread ---

class VideoWorker(QThread):
    progress = Signal(str)
    percent = Signal(int)
    finished = Signal(str)

    def __init__(self, words, title, aspect_ratio, durations, grid_size, output_path, use_images):
        super().__init__()
        self.words = [w.strip() for w in words if w.strip()]
        self.title = title
        self.aspect_ratio = aspect_ratio
        self.durations = durations
        self.grid_size = grid_size
        self.output_path = output_path
        self.use_images = use_images

    def get_font(self, size):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            try:
                return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
            except:
                return ImageFont.load_default()

    def run(self):
        try:
            total_steps = len(self.words) + 4
            step = 0

            self.progress.emit("Fetching definitions...")
            definitions = {word: get_definition(word) for word in self.words}
            step += 1
            self.percent.emit(int((step / total_steps) * 100))

            self.progress.emit("Generating puzzle grid...")
            grid, word_coords = generate_word_search(self.words, size=self.grid_size)
            step += 1
            self.percent.emit(int((step / total_steps) * 100))

            if "9:16" in self.aspect_ratio:
                width, height = 1080, 1920
            else:
                width, height = 1920, 1080

            font_huge = self.get_font(80)
            font_large = self.get_font(60)
            font_med = self.get_font(40)
            font_small = self.get_font(30)

            clips = []

            def make_clip(img, duration):
                clip = ImageClip(np.array(img)).set_duration(duration)
                return clip.crossfadein(0.5).crossfadeout(0.5)

            # 1. Intro Slide
            self.progress.emit("Rendering intro...")
            img = Image.new('RGB', (width, height), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)
            
            tw = draw.textlength(self.title, font=font_huge)
            draw.text(((width - tw)/2, height//5), self.title, fill="cyan", font=font_huge)
            
            subtitle = "Find these words:"
            tw = draw.textlength(subtitle, font=font_med)
            draw.text(((width - tw)/2, height//4 + 50), subtitle, fill="yellow", font=font_med)
            
            y_offset = height//4 + 150
            for word in self.words:
                tw = draw.textlength(word.upper(), font=font_large)
                draw.text(((width - tw)/2, y_offset), word.upper(), fill="white", font=font_large)
                y_offset += 70

            clips.append(make_clip(img, self.durations['intro']))
            step += 1
            self.percent.emit(int((step / total_steps) * 100))

            # 2. Word Search Grid Slide
            self.progress.emit("Rendering word search grid...")
            cell_size = 50 if self.grid_size <= 12 else 40
            grid_pixel_size = self.grid_size * cell_size
            start_x = (width - grid_pixel_size) // 2
            start_y = (height - grid_pixel_size) // 2 - 100
            
            def draw_grid(highlight=False):
                img = Image.new('RGB', (width, height), color=(20, 20, 30))
                draw = ImageDraw.Draw(img)
                
                # Draw words to find at the bottom
                words_str = "  |  ".join(self.words)
                wrapped_words = textwrap.fill(words_str, width=40)
                y_pos = start_y + grid_pixel_size + 40
                for line in wrapped_words.split('\n'):
                    tw = draw.textlength(line, font=font_small)
                    draw.text(((width - tw)/2, y_pos), line, fill="yellow", font=font_small)
                    y_pos += 35

                colors = ['red', 'lime', 'cyan', 'magenta', 'orange', 'deepskyblue', 'hotpink']
                
                for r in range(self.grid_size):
                    for c in range(self.grid_size):
                        x = start_x + c * cell_size
                        y = start_y + r * cell_size
                        draw.rectangle([x, y, x + cell_size, y + cell_size], outline="gray", width=1)
                        letter = grid[r][c]
                        tw = draw.textlength(letter, font=font_med)
                        draw.text((x + (cell_size - tw)/2, y + 5), letter, fill="white", font=font_med)
                
                if highlight:
                    for i, (word, coords) in enumerate(word_coords.items()):
                        color = colors[i % len(colors)]
                        for (nr, nc) in coords:
                            x = start_x + nc * cell_size
                            y = start_y + nr * cell_size
                            draw.rectangle([x, y, x + cell_size, y + cell_size], outline=color, width=4)
                return img

            clips.append(make_clip(draw_grid(False), self.durations['grid']))
            step += 1
            self.percent.emit(int((step / total_steps) * 100))

            # 3. Definitions Slides
            self.progress.emit("Rendering definitions (and fetching images)...")
            for word, definition in definitions.items():
                img = Image.new('RGB', (width, height), color=(20, 20, 30))
                draw = ImageDraw.Draw(img)
                
                w_text = f"Word: {word}"
                tw = draw.textlength(w_text, font=font_large)
                draw.text(((width - tw)/2, height//6), w_text, fill="yellow", font=font_large)
                
                # Fetch and paste image
                img_y_pos = height//6 + 100
                if self.use_images:
                    pil_img = get_wikipedia_image(word)
                    if pil_img:
                        # Resize maintaining aspect ratio
                        pil_img.thumbnail((400, 400))
                        # Paste centered
                        ix = (width - pil_img.width) // 2
                        img.paste(pil_img, (ix, img_y_pos))
                        img_y_pos += pil_img.height + 40

                # Text below image
                wrapped_def = textwrap.fill(f"Definition: {definition}", width=40)
                y_offset = img_y_pos
                for line in wrapped_def.split('\n'):
                    tw = draw.textlength(line, font=font_med)
                    draw.text(((width - tw)/2, y_offset), line, fill="white", font=font_med)
                    y_offset += 50

                clips.append(make_clip(img, self.durations['def']))
                step += 1
                self.percent.emit(int((step / total_steps) * 100))

            # 4. Solution Slide
            self.progress.emit("Rendering solution...")
            img_sol = draw_grid(True)
            draw = ImageDraw.Draw(img_sol)
            txt = "Here are the answers!"
            tw = draw.textlength(txt, font=font_large)
            draw.text(((width - tw)/2, 50), txt, fill="white", font=font_large)
            
            clips.append(make_clip(img_sol, self.durations['grid']))

            # Combine and save
            self.progress.emit("Compiling MP4 video...")
            final_clip = concatenate_videoclips(clips, method="compose", padding=-0.5)
            final_clip.write_videofile(self.output_path, fps=24, codec='libx264', audio=False, verbose=False, logger=None)
            
            self.percent.emit(100)
            self.finished.emit(f"Success! Video saved to:\n{self.output_path}")

        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")

# --- Main GUI ---

class WordSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("YouTube Word Search Generator Pro+")
        self.resize(650, 750)

        main_layout = QVBoxLayout()

        # --- Word Input Group ---
        input_group = QGroupBox("1. Content")
        input_layout = QVBoxLayout()
        
        input_layout.addWidget(QLabel("Video Title:"))
        self.title_input = QLineEdit("Vocabulary Challenge")
        input_layout.addWidget(self.title_input)

        input_layout.addWidget(QLabel("Enter words (one word per line):"))
        self.word_input = QPlainTextEdit()
        self.word_input.setPlaceholderText("apple\nbanana\norange\ngrape")
        input_layout.addWidget(self.word_input)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # --- Settings Group ---
        settings_group = QGroupBox("2. Video Settings")
        form_layout = QFormLayout()

        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["9:16 (Shorts)", "16:9 (Standard YouTube)"])
        form_layout.addRow("Aspect Ratio:", self.aspect_combo)

        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["10x10 (Easy)", "12x12 (Medium)", "15x15 (Hard)"])
        form_layout.addRow("Grid Size:", self.grid_combo)

        dur_layout = QHBoxLayout()
        self.intro_dur = QSpinBox(); self.intro_dur.setRange(1, 15); self.intro_dur.setValue(4)
        self.grid_dur = QSpinBox(); self.grid_dur.setRange(1, 30); self.grid_dur.setValue(6)
        self.def_dur = QSpinBox(); self.def_dur.setRange(1, 15); self.def_dur.setValue(4)
        
        dur_layout.addWidget(QLabel("Intro:")); dur_layout.addWidget(self.intro_dur)
        dur_layout.addWidget(QLabel("Grid:")); dur_layout.addWidget(self.grid_dur)
        dur_layout.addWidget(QLabel("Defs:")); dur_layout.addWidget(self.def_dur)
        form_layout.addRow("Durations (sec):", dur_layout)

        self.img_check = QCheckBox("Fetch Wikipedia Images for definitions")
        self.img_check.setChecked(True)
        form_layout.addRow("Visuals:", self.img_check)

        settings_group.setLayout(form_layout)
        main_layout.addWidget(settings_group)

        # --- Output Group ---
        output_group = QGroupBox("3. Output")
        output_layout = QHBoxLayout()
        self.output_path_btn = QPushButton("Choose Save Location...")
        self.output_path_btn.clicked.connect(self.select_save_file)
        output_layout.addWidget(self.output_path_btn)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # --- Generate & Status ---
        self.generate_btn = QPushButton("Generate Video")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.generate_btn.clicked.connect(self.start_generation)
        main_layout.addWidget(self.generate_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        main_layout.addWidget(QLabel("Status Log:"))
        self.status_box = QPlainTextEdit()
        self.status_box.setReadOnly(True)
        main_layout.addWidget(self.status_box)

        self.setLayout(main_layout)

    def select_save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "word_search_video.mp4", "MP4 Files (*.mp4)")
        if file_path:
            if not file_path.endswith('.mp4'):
                file_path += '.mp4'
            self.output_path_btn.setText(file_path)

    def log(self, message):
        self.status_box.appendPlainText(message)

    def start_generation(self):
        words = self.word_input.toPlainText().split('\n')
        words = [w.strip() for w in words if w.strip()]
        
        if not words:
            QMessageBox.warning(self, "Input Error", "Please enter at least one word.")
            return

        output_path = self.output_path_btn.text()
        if "Choose Save" in output_path:
            QMessageBox.warning(self, "Output Error", "Please choose a save location for the MP4 file.")
            return

        grid_size_str = self.grid_combo.currentText().split("x")[0]
        grid_size = int(grid_size_str)

        durations = {
            'intro': self.intro_dur.value(),
            'grid': self.grid_dur.value(),
            'def': self.def_dur.value()
        }

        self.generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_box.clear()
        self.log("Starting process...")

        # Setup Thread
        self.worker = VideoWorker(
            words, self.title_input.text(), self.aspect_combo.currentText(), 
            durations, grid_size, output_path, self.img_check.isChecked()
        )
        self.worker.progress.connect(self.log)
        self.worker.percent.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, message):
        self.log(message)
        self.generate_btn.setEnabled(True)
        if "Success" in message:
            QMessageBox.information(self, "Done", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WordSearchApp()
    window.show()
    sys.exit(app.exec())