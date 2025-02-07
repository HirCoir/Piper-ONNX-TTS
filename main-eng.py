import os
import sys
import random
import string
import subprocess
import requests
import json
import re
import logging
import tempfile
import concurrent.futures
import signal
import shutil
import markdown
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QHBoxLayout, QFileDialog, QComboBox,
    QMessageBox, QSlider, QDialog, QAction, QMenu,
    QSizePolicy, QSpacerItem, QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QInputDialog
)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import (QIcon, QTextDocument, QFont, QPalette, QColor,
                        QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import webbrowser

# Configure logging
logging.basicConfig(level=logging.ERROR)

# Define paths and folders
def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running in normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

file_folder = get_base_path()
temp_audio_folder = os.path.join(file_folder, 'temp_audio')
model_folder = os.path.join(os.path.expanduser('~'), 'Documents', 'ONNX-TTS')
piper_binary_path = os.path.join(file_folder, 'piper', 'piper.exe')
icon_path = os.path.join(file_folder, 'icon.ico')
play_icon_path = os.path.join(file_folder, 'play.png')
pause_icon_path = os.path.join(file_folder, 'pause.png')
ffmpeg_path = os.path.join(file_folder, 'ffmpeg.exe')

# Create necessary directories
os.makedirs(temp_audio_folder, exist_ok=True)
os.makedirs(model_folder, exist_ok=True)

# Global replacements and text processing parameters
global_replacements = [('\n', ' '), ('"', ''), ("'", ""), ('*', '')]

# Custom button styles
BUTTON_STYLE = """
QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 100px;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QPushButton:hover {
    background-color: #45a049;
}
QPushButton:pressed {
    background-color: #388E3C;
}
QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}
"""

STOP_BUTTON_STYLE = """
QPushButton {
    background-color: #f44336;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #d32f2f;
}
QPushButton:pressed {
    background-color: #b71c1c;
}
"""

SLIDER_STYLE = """
QSlider::groove:horizontal {
    border: 1px solid #999999;
    height: 8px;
    background: #4CAF50;
    margin: 2px 0;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: white;
    border: 1px solid #5c5c5c;
    width: 18px;
    margin: -2px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #f0f0f0;
}
"""

# Function to get process creation flags
def get_creationflags():
    return subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

class ThemeManager:
    @staticmethod
    def dark_theme():
        return """
            QWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            QTextEdit, QComboBox, QLineEdit, QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #4CAF50;
            }
            QMenu {
                background-color: #353535;
                border: 1px solid #454545;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """

    @staticmethod
    def light_theme():
        return """
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            QTextEdit, QComboBox, QLineEdit, QListWidget {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #4CAF50;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #dddddd;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """

class TextHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        silence_format = QTextCharFormat()
        silence_format.setForeground(QColor('#FF69B4'))
        self.highlighting_rules.append((re.compile(r'<#\d+\.?\d*#>'), silence_format))
        voice_format = QTextCharFormat()
        voice_format.setForeground(QColor('#00FF00'))
        self.highlighting_rules.append((re.compile(r'<#[\w-]+#>'), voice_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)

class FindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Text")
        self.setWindowIcon(QIcon(icon_path))
        self.parent = parent
        layout = QVBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        layout.addWidget(self.search_input)
        self.setLayout(layout)
        self.search_input.textChanged.connect(self.highlight_matches)

    def highlight_matches(self):
        search_text = self.search_input.text()
        cursor = self.parent.text_input.textCursor()
        format = QTextCharFormat()
        format.setBackground(QColor("#FFD700"))
        self.parent.text_input.blockSignals(True)
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()
        if search_text:
            document = self.parent.text_input.document()
            regex = re.compile(re.escape(search_text), re.IGNORECASE)
            pos = 0
            while True:
                match = regex.search(document.toPlainText(), pos)
                if not match:
                    break
                start = match.start()
                end = match.end()
                cursor.setPosition(start)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, end - start)
                cursor.mergeCharFormat(format)
                pos = end
        cursor.endEditBlock()
        self.parent.text_input.blockSignals(False)

class ModelSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Model")
        self.setWindowIcon(QIcon(icon_path))
        self.selected_model_name = None
        layout = QVBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search model...")
        layout.addWidget(self.search_bar)
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.model_list)
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton('Accept')
        self.ok_button.clicked.connect(self.accept_selection)
        self.ok_button.setEnabled(False)
        self.ok_button.setStyleSheet(BUTTON_STYLE)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.search_bar.textChanged.connect(self.filter_models)
        self.model_list.itemSelectionChanged.connect(self.update_buttons)
        self.load_models()

    def load_models(self):
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.onnx')]
        models = [os.path.splitext(f)[0] for f in model_files]
        self.model_list.addItems(models)

    def filter_models(self, text):
        self.model_list.clear()
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.onnx')]
        models = [os.path.splitext(f)[0] for f in model_files]
        filtered = [m for m in models if text.lower() in m.lower()]
        self.model_list.addItems(filtered)

    def update_buttons(self):
        has_selection = len(self.model_list.selectedItems()) > 0
        self.ok_button.setEnabled(has_selection)

    def accept_selection(self):
        selected = self.model_list.currentItem()
        if selected:
            self.selected_model_name = selected.text()
            self.accept()

    def selected_model(self):
        return self.selected_model_name

class ConvertTextToSpeechThread(QThread):
    conversion_done = pyqtSignal(str)
    def __init__(self, text, default_model):
        super().__init__()
        self.text = text
        self.default_model = default_model
        self.running = True
        self.piper_processes = []

    def run(self):
        result = self.convert_text_to_speech(self.text, self.default_model)
        self.conversion_done.emit(result if result else None)

    def stop(self):
        self.running = False
        for process in self.piper_processes:
            try:
                os.kill(process.pid, signal.SIGTERM)
            except:
                pass
        self.piper_processes.clear()

    def convert_text_to_speech(self, text, default_model):
        try:
            # Remove any previous final file in the temp_audio_folder
            for file_name in os.listdir(temp_audio_folder):
                file_path = os.path.join(temp_audio_folder, file_name)
                if file_name.startswith("final_") and file_name.endswith(".wav"):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logging.error(f"Error deleting previous final audio file: {str(e)}")

            text = filter_code_blocks(text)
            text = process_line_breaks(text)
            text = multiple_replace(text, global_replacements)
            text = text.replace('\\', '\\\\').replace('"', '\\"')
            segments = re.split(r'(<#.*?#>)', text)
            temp_dir = tempfile.mkdtemp(dir=temp_audio_folder)
            audio_segments = []
            num_workers = 2 * os.cpu_count()
            current_model = default_model
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                for segment in segments:
                    if not self.running:
                        for file in audio_segments:
                            try:
                                os.remove(file)
                            except:
                                pass
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
                        return None
                    if not segment:
                        continue
                    processed_as_tag = False
                    if segment.startswith('<#') and segment.endswith('#>'):
                        silence_match = re.match(r'<#(\d+\.?\d*)#>', segment)
                        if silence_match:
                            seconds = float(silence_match.group(1))
                            silence_file = generate_silence(seconds, temp_dir)
                            if silence_file:
                                audio_segments.append(silence_file)
                            processed_as_tag = True
                        else:
                            model_match = re.match(r'<#([\w-]+)#>', segment)
                            if model_match:
                                model_name = model_match.group(1)
                                if model_name == 'default':
                                    current_model = default_model
                                    processed_as_tag = True
                                else:
                                    model_path = os.path.join(model_folder, f"{model_name}.onnx")
                                    if os.path.exists(model_path):
                                        current_model = model_name
                                        processed_as_tag = True
                    if processed_as_tag:
                        continue
                    model_path = os.path.join(model_folder, f"{current_model}.onnx")
                    if not os.path.exists(model_path):
                        logging.error(f"Model {current_model} not found, skipping segment: {segment}")
                        continue
                    filtered_text = filter_text_segment(segment)
                    sentences = split_sentences(filtered_text)
                    futures = []
                    for sentence in sentences:
                        if sentence:
                            future = executor.submit(self.generate_audio_with_process, sentence, model_path, temp_dir)
                            futures.append(future)
                    for future in futures:
                        if not self.running:
                            break
                        audio_file = future.result()
                        if audio_file:
                            audio_segments.append(audio_file)
                    if not self.running:
                        break
            if not self.running:
                return None
            final_output = os.path.join(temp_audio_folder, f"final_{random_string()}.wav")
            if not concatenate_audio_files(audio_segments, final_output, temp_dir):
                return None

            # Remove temporary files after concatenation
            for file in audio_segments:
                try:
                    os.remove(file)
                except:
                    pass
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

            return final_output
        except Exception as e:
            logging.error(f"Error in conversion: {str(e)}")
            return None
        finally:
            for file in audio_segments:
                try:
                    os.remove(file)
                except:
                    pass
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception as e:
                    logging.error(f"Error cleaning temporary files: {str(e)}")

    def generate_audio_with_process(self, text_part, model_path, temp_dir):
        filtered_text = filter_text_segment(text_part)
        if not filtered_text:
            return None
        output_file = os.path.join(temp_dir, f"audio_{random_string()}.wav")
        try:
            command = [piper_binary_path, '-m', model_path, '-f', output_file]
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=get_creationflags()
            )
            self.piper_processes.append(process)
            process.communicate(input=filtered_text, timeout=30)
            self.piper_processes.remove(process)
            return output_file if process.returncode == 0 else None
        except Exception as e:
            logging.error(f"Error generating audio: {str(e)}")
            if process in self.piper_processes:
                self.piper_processes.remove(process)
            return None

class DownloadModelThread(QThread):
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    def __init__(self, model_key, files):
        super().__init__()
        self.model_key = model_key
        self.files = files

    def run(self):
        total_files = len(self.files)
        current_file = 0
        for file_path, file_info in self.files.items():
            if file_path.endswith(".onnx") or file_path.endswith(".onnx.json"):
                file_url = file_info['url']
                file_name = os.path.basename(file_path)
                destination = os.path.join(model_folder, file_name)
                download_file(file_url, destination, self.update_progress)
                current_file += 1
                progress = int((current_file / total_files) * 100)
                self.progress_updated.emit(progress)
        self.download_finished.emit(self.model_key)

    def update_progress(self, downloaded_size, total_size):
        if total_size > 0:
            progress = int((downloaded_size / total_size) * 100)
            self.progress_updated.emit(progress)

class DownloadModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Download Model')
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon(icon_path))
        layout = QVBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Search model...')
        self.search_bar.textChanged.connect(self.filter_models)
        layout.addWidget(self.search_bar)
        self.model_list = QListWidget()
        layout.addWidget(self.model_list)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.download_button = QPushButton('Download Selected Model')
        self.download_button.clicked.connect(self.download_selected_model)
        self.download_button.setStyleSheet(BUTTON_STYLE)
        layout.addWidget(self.download_button)
        self.manage_models_button = QPushButton('Manage Models')
        self.manage_models_button.clicked.connect(self.show_manage_models_dialog)
        self.manage_models_button.setStyleSheet(BUTTON_STYLE)
        layout.addWidget(self.manage_models_button)
        self.setLayout(layout)
        self.download_thread = None
        self.filter_models('')

    def filter_models(self, text):
        self.model_list.clear()
        sorted_models = sorted(voices_data.keys(), key=lambda x: x.lower())
        filtered_models = [model for model in sorted_models if text.lower() in model.lower()]
        self.model_list.addItems(filtered_models)

    def download_selected_model(self):
        selected_items = self.model_list.selectedItems()
        if selected_items:
            selected_key = selected_items[0].text()
            if selected_key in voices_data:
                self.check_license(selected_key)
            else:
                QMessageBox.critical(self, "Error", "Model not found.")
        else:
            QMessageBox.warning(self, "Warning", "Please select a model to download.")

    def check_license(self, model_key):
        model_info = voices_data[model_key]
        license_file = None
        for file_path in model_info['files']:
            if file_path.lower().endswith('license.md'):
                license_file = file_path
                break
        if license_file:
            temp_dir = tempfile.mkdtemp()
            license_url = model_info['files'][license_file]['url']
            license_path = os.path.join(temp_dir, 'license.md')
            try:
                download_file(license_url, license_path, lambda x, y: None)
                with open(license_path, 'r', encoding='utf-8') as f:
                    license_content = f.read()
                self.show_license_dialog(license_content, model_key)
            except Exception as e:
                logging.error(f"Error obtaining license: {str(e)}")
                self.start_download(model_key)
            finally:
                shutil.rmtree(temp_dir)
        else:
            self.start_download(model_key)

    def show_license_dialog(self, license_content, model_key):
        dialog = QDialog(self)
        dialog.setWindowTitle("License Agreement")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        html_content = markdown.markdown(license_content)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html_content)
        layout.addWidget(text_edit)
        button_box = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        accept_btn.clicked.connect(lambda: self.on_license_response(True, dialog, model_key))
        accept_btn.setStyleSheet(BUTTON_STYLE)
        reject_btn = QPushButton("Reject")
        reject_btn.clicked.connect(lambda: self.on_license_response(False, dialog, model_key))
        reject_btn.setStyleSheet(BUTTON_STYLE)
        button_box.addWidget(accept_btn)
        button_box.addWidget(reject_btn)
        layout.addLayout(button_box)
        dialog.setLayout(layout)
        dialog.exec_()

    def on_license_response(self, accepted, dialog, model_key):
        dialog.close()
        if accepted:
            self.start_download(model_key)
        else:
            self.parent().audio_label.setText("Download canceled by user")

    def start_download(self, model_key):
        model_info = voices_data[model_key]
        files = model_info["files"]
        base_model_key = model_info['base_model_key']
        self.download_thread = DownloadModelThread(base_model_key, files)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_button.setEnabled(False)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def download_finished(self, model_key):
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.parent().update_model_spinner()
        self.parent().audio_label.setText(f'Model {model_key} downloaded successfully.')

    def show_manage_models_dialog(self):
        dialog = ManageModelsDialog(self, self.parent())
        dialog.exec_()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setGeometry(100, 100, 400, 300)
        self.setWindowIcon(QIcon(icon_path))
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.labels = {}
        self.sliders = {}
        self.create_slider('Speaker', 0, 10, self.parent().speaker, self.set_speaker)
        self.create_slider('Noise Scale', 0, 100, int(self.parent().noise_scale * 100), self.set_noise_scale)
        self.create_slider('Length Scale', 0, 100, int(self.parent().length_scale * 100), self.set_length_scale)
        self.create_slider('Noise W', 0, 100, int(self.parent().noise_w * 100), self.set_noise_w)
        self.create_slider('Sentence Silence', 0, 100, int(self.parent().sentence_silence * 100), self.set_sentence_silence)
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton('Reset')
        self.reset_button.clicked.connect(self.reset_values)
        self.reset_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.reset_button)
        self.help_button = QPushButton('Help')
        self.help_button.clicked.connect(self.open_help_url)
        self.help_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.help_button)
        main_layout.addLayout(button_layout)
        self.powered_by = QLabel('<a href="https://youtube.com/@hircoir" style="color: #4CAF50;">Powered by HirCoir</a>')
        self.powered_by.setOpenExternalLinks(True)
        self.powered_by.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.powered_by)

    def create_slider(self, name, min_value, max_value, current_value, connect_function):
        label = QLabel(f'{name}: {current_value}')
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue(current_value)
        slider.valueChanged.connect(connect_function)
        slider.setStyleSheet(SLIDER_STYLE)
        self.layout().addWidget(label)
        self.layout().addWidget(slider)
        self.labels[name] = label
        self.sliders[name] = slider
        return label, slider

    def set_speaker(self, value):
        self.parent().speaker = value
        self.labels['Speaker'].setText(f'Speaker: {value}')

    def set_noise_scale(self, value):
        self.parent().noise_scale = value / 100
        self.labels['Noise Scale'].setText(f'Noise Scale: {value / 100:.2f}')

    def set_length_scale(self, value):
        self.parent().length_scale = value / 100
        self.labels['Length Scale'].setText(f'Length Scale: {value / 100:.2f}')

    def set_noise_w(self, value):
        self.parent().noise_w = value / 100
        self.labels['Noise W'].setText(f'Noise W: {value / 100:.2f}')

    def set_sentence_silence(self, value):
        self.parent().sentence_silence = value / 100
        self.labels['Sentence Silence'].setText(f'Sentence Silence: {value / 100:.2f}')

    def reset_values(self):
        default_values = {
            'Speaker': 0,
            'Noise Scale': 66,
            'Length Scale': 100,
            'Noise W': 80,
            'Sentence Silence': 20
        }
        for name, value in default_values.items():
            self.sliders[name].setValue(value)

    def open_help_url(self):
        webbrowser.open('https://www.hircoir.eu.org/onnx-tts/help.html')

class TTSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_file = None
        self.conversion_thread = None
        self.volume = 100
        self.speaker = 0
        self.noise_scale = 0.667
        self.length_scale = 1.0
        self.noise_w = 0.8
        self.sentence_silence = 0.2
        self.remove_style_enabled = False
        self.processing_text = False
        self.dark_mode = True
        self.download_dialog = None
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle('ONNX - Text to Speech Converter')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(icon_path))
        layout = QVBoxLayout()
        title = QLabel('Text to Audio Converter')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 20px;')
        layout.addWidget(title)
        self.text_input = QTextEdit()
        self.highlighter = TextHighlighter(self.text_input.document())
        self.text_input.setPlaceholderText('Enter text here')
        self.text_input.textChanged.connect(self.on_text_changed)
        self.text_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_input.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.text_input, 1)
        model_layout = QHBoxLayout()
        self.model_spinner = QComboBox()
        self.model_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_spinner.setFixedHeight(40)
        self.model_spinner.addItem("Select a model")
        self.update_model_spinner()
        model_layout.addWidget(self.model_spinner)
        self.download_button = QPushButton('Download Model')
        self.download_button.clicked.connect(self.show_download_dialog)
        self.download_button.setStyleSheet(BUTTON_STYLE)
        model_layout.addWidget(self.download_button)
        if not voices_data:
            self.download_button.setEnabled(False)
        layout.addLayout(model_layout)
        button_layout = QHBoxLayout()
        self.convert_button = QPushButton('Generate Audio')
        self.convert_button.clicked.connect(self.convert_text)
        self.convert_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.convert_button)
        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_conversion)
        self.stop_button.setVisible(False)
        self.stop_button.setStyleSheet(STOP_BUTTON_STYLE)
        button_layout.addWidget(self.stop_button)
        self.save_button = QPushButton('Save Audio')
        self.save_button.clicked.connect(self.save_audio)
        self.save_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.save_button)
        self.settings_button = QPushButton('Model Settings')
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.settings_button)
        self.theme_button = QPushButton('Change Theme')
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.theme_button)
        layout.addLayout(button_layout)
        self.audio_label = QLabel('Audio will be played here')
        self.audio_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.audio_label)
        self.audio_controls = QHBoxLayout()
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(play_icon_path))
        self.play_button.clicked.connect(self.play_audio)
        self.play_button.setStyleSheet(BUTTON_STYLE)
        self.audio_controls.addWidget(self.play_button)
        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon(pause_icon_path))
        self.pause_button.clicked.connect(self.pause_audio)
        self.pause_button.setStyleSheet(BUTTON_STYLE)
        self.audio_controls.addWidget(self.pause_button)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self.set_position)
        self.slider.sliderPressed.connect(self.pause_audio)
        self.slider.sliderReleased.connect(self.play_audio)
        self.slider.setStyleSheet(SLIDER_STYLE)
        self.audio_controls.addWidget(self.slider)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setStyleSheet(SLIDER_STYLE)
        self.audio_controls.addWidget(QLabel('Volume'))
        self.audio_controls.addWidget(self.volume_slider)
        self.duration_label = QLabel('00:00 / 00:00')
        self.audio_controls.addWidget(self.duration_label)
        layout.addLayout(self.audio_controls)
        self.setLayout(layout)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.find_shortcut = QAction("Find", self)
        self.find_shortcut.setShortcut(QKeySequence.Find)
        self.find_shortcut.triggered.connect(self.show_find_dialog)
        self.addAction(self.find_shortcut)

    def apply_theme(self):
        app = QApplication.instance()
        if self.dark_mode:
            app.setStyleSheet(ThemeManager.dark_theme())
        else:
            app.setStyleSheet(ThemeManager.light_theme())

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def convert_text(self):
        text = self.text_input.toPlainText()
        model_name = self.model_spinner.currentText()
        if model_name == "Select a model":
            QMessageBox.warning(self, 'Error', 'Please select a base model before generating audio.')
            return
        self.audio_label.setText('Generating audio...')
        self.conversion_thread = ConvertTextToSpeechThread(text, model_name)
        self.conversion_thread.conversion_done.connect(self.handle_conversion_done)
        self.conversion_thread.start()
        self.convert_button.setVisible(False)
        self.stop_button.setVisible(True)

    def stop_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.stop()
            self.audio_label.setText('Audio generation stopped')
            self.convert_button.setVisible(True)
            self.stop_button.setVisible(False)

    def handle_conversion_done(self, output_file):
        self.convert_button.setVisible(True)
        self.stop_button.setVisible(False)
        if output_file:
            self.audio_file = output_file
            self.audio_label.setText('Audio generated')
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(output_file)))
            self.player.setVolume(self.volume)
            self.play_audio()
        else:
            self.audio_label.setText('Failed to generate audio.')

    def play_audio(self):
        if self.audio_file:
            self.player.play()

    def pause_audio(self):
        self.player.pause()

    def set_position(self, position):
        self.player.setPosition(position)

    def update_position(self, position):
        self.slider.setValue(position)
        self.update_duration_label(position)

    def update_duration(self, duration):
        self.slider.setRange(0, duration)
        self.update_duration_label(0)

    def update_duration_label(self, position):
        duration = self.player.duration()
        if duration > 0:
            total_seconds = duration // 1000
            current_seconds = position // 1000
            total_minutes, total_seconds = divmod(total_seconds, 60)
            current_minutes, current_seconds = divmod(current_seconds, 60)
            self.duration_label.setText(f'{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}')

    def set_volume(self, volume):
        self.volume = volume
        self.player.setVolume(volume)

    def save_audio(self):
        if self.audio_file:
            save_path, _ = QFileDialog.getSaveFileName(self, 'Save Audio File', '', 'Audio Files (*.wav)')
            if save_path:
                os.rename(self.audio_file, save_path)
                self.audio_file = save_path
                QMessageBox.information(self, 'File Saved', 'The audio file has been saved successfully')

    def show_settings(self):
        self.settings_button.setEnabled(False)
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.finished.connect(lambda: self.settings_button.setEnabled(True))
        self.settings_dialog.show()

    def show_download_dialog(self):
        if self.download_dialog is None:
            self.download_dialog = DownloadModelDialog(self)
            self.download_dialog.finished.connect(self.on_download_dialog_finished)
            self.download_dialog.show()
            self.download_button.setEnabled(False)

    def on_download_dialog_finished(self):
        self.download_dialog = None
        self.download_button.setEnabled(True)

    def update_model_spinner(self):
        self.model_spinner.clear()
        self.model_spinner.addItem("Select a model")
        downloaded_models = [f for f in os.listdir(model_folder) if f.endswith('.onnx')]
        models_with_authors = []
        for model in downloaded_models:
            model_name = os.path.splitext(model)[0]
            found = False
            for full_name, data in voices_data.items():
                if data['base_model_key'] == model_name:
                    models_with_authors.append(full_name)
                    found = True
                    break
            if not found:
                models_with_authors.append(model_name)
        self.model_spinner.addItems(sorted(models_with_authors))

    def on_text_changed(self):
        if self.processing_text:
            return
        self.processing_text = True
        cursor = self.text_input.textCursor()
        position = cursor.position()
        self.highlighter.rehighlight()
        cursor.setPosition(position)
        self.text_input.setTextCursor(cursor)
        self.processing_text = False

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.text_input.copy)
        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.text_input.paste)
        paste_without_formatting_action = QAction("Paste without formatting", self)
        paste_without_formatting_action.triggered.connect(self.paste_without_formatting)
        model_action = QAction("Model Speaker", self)
        model_action.triggered.connect(self.insert_model_tag)
        reset_action = QAction("Reset Model", self)
        reset_action.triggered.connect(lambda: self.insert_text_at_cursor("<#default#>"))
        insert_silence_action = QAction("Insert Silence", self)
        insert_silence_action.triggered.connect(self.insert_silence)
        context_menu.addAction(copy_action)
        context_menu.addAction(paste_action)
        context_menu.addAction(paste_without_formatting_action)
        context_menu.addSeparator()
        context_menu.addAction(model_action)
        context_menu.addAction(reset_action)
        context_menu.addAction(insert_silence_action)
        context_menu.exec_(self.text_input.mapToGlobal(pos))

    def paste_without_formatting(self):
        cursor = self.text_input.textCursor()
        mime_data = QApplication.clipboard().mimeData()
        if mime_data.hasText():
            cursor.insertText(mime_data.text())
        self.text_input.setTextCursor(cursor)

    def insert_model_tag(self):
        dialog = ModelSelectorDialog(self)
        if dialog.exec_():
            selected_model = dialog.selected_model()
            if selected_model:
                self.insert_text_at_cursor(f"<#{selected_model}#>")

    def insert_text_at_cursor(self, text):
        cursor = self.text_input.textCursor()
        cursor.insertText(text)
        self.text_input.setTextCursor(cursor)

    def insert_silence(self):
        duration, ok = QInputDialog.getDouble(self, "Insert Silence", "Duration of silence (seconds):", 0.0, 0.0, 1000.0, 2)
        if ok:
            self.insert_text_at_cursor(f"<#{duration}#>")

    def show_find_dialog(self):
        dialog = FindDialog(self)
        dialog.exec_()

class ManageModelsDialog(QDialog):
    def __init__(self, parent=None, main_app=None):
        super().__init__(parent)
        self.main_app = main_app
        self.setWindowTitle('Manage Models')
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon(icon_path))
        layout = QVBoxLayout()
        self.model_list = QListWidget()
        self.model_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.model_list)
        button_layout = QHBoxLayout()
        self.delete_button = QPushButton('Delete Selected Models')
        self.delete_button.clicked.connect(self.delete_selected_models)
        self.delete_button.setStyleSheet(BUTTON_STYLE)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.load_models()

    def load_models(self):
        self.model_list.clear()
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.onnx')]
        models = [os.path.splitext(f)[0] for f in model_files]
        self.model_list.addItems(models)

    def delete_selected_models(self):
        selected_items = self.model_list.selectedItems()
        if selected_items:
            confirm = QMessageBox.question(self, 'Confirm Deletion',
                                            'Are you sure you want to delete the selected models?',
                                            QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                for item in selected_items:
                    model_name = item.text()
                    model_path = os.path.join(model_folder, f"{model_name}.onnx")
                    if os.path.exists(model_path):
                        os.remove(model_path)
                self.load_models()
                self.main_app.update_model_spinner()

def random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def multiple_replace(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    return text

def filter_code_blocks(text):
    return re.sub(r'```[^`\n]*\n.*?```', '', text, flags=re.DOTALL)

def process_line_breaks(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ''
    processed = [lines[0]]
    for line in lines[1:]:
        prev_line = processed[-1]
        if prev_line and prev_line[-1] in ('.', ','):
            processed.append(' ' + line)
        else:
            if prev_line.endswith(')'):
                processed.append(', ' + line)
            else:
                processed.append('. ' + line)
    processed_text = ''.join(processed)
    processed_text = re.sub(r'(\))(?![.,])(?=\s|\\\\$)', r'\1,', processed_text)
    return processed_text

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def filter_text_segment(text_segment):
    text = filter_code_blocks(text_segment)
    text = process_line_breaks(text)
    text = multiple_replace(text, global_replacements)
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    return text[:100000]

def generate_silence(seconds, temp_dir):
    if seconds <= 0:
        return None
    output_file = os.path.join(temp_dir, f"silence_{seconds}s.wav")
    try:
        subprocess.run(
            [
                ffmpeg_path,
                '-loglevel', 'error',
                '-f', 'lavfi',
                '-i', 'anullsrc=r=22050:cl=mono',
                '-t', str(seconds),
                '-ar', '22050',
                '-y',
                output_file
            ],
            check=True,
            creationflags=get_creationflags()
        )
        return output_file
    except subprocess.CalledProcessError:
        logging.error("Error generating silence")
        return None

def concatenate_audio_files(audio_files, output_file, temp_dir):
    list_file = os.path.join(temp_dir, 'concat_list.txt')
    try:
        with open(list_file, 'w') as f:
            for file in audio_files:
                f.write(f"file '{os.path.abspath(file)}'\n")
        subprocess.run(
            [
                ffmpeg_path,
                '-loglevel', 'error',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',
                output_file
            ],
            check=True,
            creationflags=get_creationflags()
        )
        return True
    except subprocess.CalledProcessError:
        logging.error("Error concatenating audios")
        return False
    finally:
        try:
            os.remove(list_file)
        except:
            pass

def download_file(url, destination, progress_callback):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0
    with open(destination, 'wb') as file:
        for data in response.iter_content(1024):
            file.write(data)
            downloaded_size += len(data)
            progress_callback(downloaded_size, total_size)

if __name__ == '__main__':
    # Check if FFmpeg exists
    if not os.path.exists(ffmpeg_path):
        print(f"Error: FFmpeg not found at {ffmpeg_path}")
        sys.exit(1)

    repos_url = "https://raw.githubusercontent.com/HirCoir/bash-logs/refs/heads/main/piper_voices.json"
    voices_data = {}
    try:
        repos_response = requests.get(repos_url)
        repos_response.raise_for_status()
        repos = repos_response.json()
        for repo in repos:
            repo_base_url = repo['base_url']
            repo_json_url = repo['json_url']
            autor = repo['author_repo']
            try:
                repo_response = requests.get(repo_json_url)
                repo_response.raise_for_status()
                repo_voices = repo_response.json()
                for model_key, model_info in repo_voices.items():
                    updated_files = {}
                    for file_path, file_details in model_info.get('files', {}).items():
                        full_url = repo_base_url + file_path
                        updated_files[file_path] = {
                            'url': full_url,
                            'size': file_details.get('size', 0)
                        }
                    voices_data[model_key] = {
                        'files': updated_files,
                        'Author': autor,
                        'base_model_key': model_key
                    }
            except requests.RequestException as e:
                logging.error(f"Error loading repository {repo_json_url}: {e}")
    except requests.RequestException as e:
        logging.error(f"Error loading repos.json: {e}")
        voices_data = {}

    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(ThemeManager.dark_theme())
    tts_app = TTSApp()
    tts_app.show()
    app.exec_()
