import os
import random
import string
import subprocess
import requests
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit,
                             QPushButton, QHBoxLayout, QFileDialog, QComboBox,
                             QMessageBox, QSlider, QDialog, QAction, QMenu,
                             QSizePolicy, QSpacerItem, QLineEdit, QListWidget, QListWidgetItem, QProgressBar)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QTextDocument, QFont, QPalette, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import webbrowser

# Define the directory where files are saved
file_folder = os.path.dirname(os.path.abspath(__file__))
temp_audio_folder = os.path.join(file_folder, 'temp_audio')
model_folder = os.path.join(os.path.expanduser('~'), 'Documents', 'ONNX-TTS')
piper_binary_path = os.path.join(file_folder, 'piper', 'piper.exe')
icon_path = os.path.join(file_folder, 'icon.ico')
play_icon_path = os.path.join(file_folder, 'play.png')
pause_icon_path = os.path.join(file_folder, 'pause.png')

# Create the temp_audio folder if it does not exist
os.makedirs(temp_audio_folder, exist_ok=True)
os.makedirs(model_folder, exist_ok=True)

# JSON URL
json_url = "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json"

# Download and parse the JSON
try:
    response = requests.get(json_url)
    response.raise_for_status()  # Raises an exception if the request fails
    voices_data = response.json()
except requests.RequestException:
    voices_data = {}

# Base URL for downloading files
base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"

# Function to download a file
def download_file(url, destination, progress_callback):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0
    with open(destination, 'wb') as file:
        for data in response.iter_content(1024):
            file.write(data)
            downloaded_size += len(data)
            progress_callback(downloaded_size, total_size)

class ConvertTextToSpeechThread(QThread):
    conversion_done = pyqtSignal(str)

    def __init__(self, text, model_path, output_file, speaker, noise_scale, length_scale, noise_w, sentence_silence):
        super().__init__()
        self.text = text
        self.model_path = model_path
        self.output_file = output_file
        self.speaker = speaker
        self.noise_scale = noise_scale
        self.length_scale = length_scale
        self.noise_w = noise_w
        self.sentence_silence = sentence_silence

    def run(self):
        temp_txt_path = os.path.join(os.getenv('TEMP'), "temp_text.txt")
        with open(temp_txt_path, "w", encoding="utf-8") as f:
            f.write(self.text)

        command = (f'type "{temp_txt_path}" | "{piper_binary_path}" -m "{self.model_path}" -f "{self.output_file}" '
                   f'--speaker {self.speaker} --noise_scale {self.noise_scale} --length_scale {self.length_scale} '
                   f'--noise_w {self.noise_w} --sentence_silence {self.sentence_silence}')
        try:
            subprocess.run(command, shell=True, check=True)
            if os.path.exists(self.output_file):
                self.conversion_done.emit(self.output_file)
            else:
                self.conversion_done.emit(None)
        except subprocess.CalledProcessError:
            self.conversion_done.emit(None)
        finally:
            os.remove(temp_txt_path)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setGeometry(100, 100, 400, 300)
        self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet('''
            QDialog {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                margin: 5px;
                border-radius: 3px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        ''')

        layout = QVBoxLayout()
        self.setLayout(layout)

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
        button_layout.addWidget(self.reset_button)

        self.help_button = QPushButton('Help')
        self.help_button.clicked.connect(self.open_help_url)
        button_layout.addWidget(self.help_button)

        layout.addLayout(button_layout)

        # Add the "Powered by HirCoir" link
        self.powered_by = QLabel('<a href="https://youtube.com/@hircoir" style="color: #4CAF50;">Powered by HirCoir</a>')
        self.powered_by.setOpenExternalLinks(True)
        self.powered_by.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.powered_by)

    def create_slider(self, name, min_value, max_value, current_value, connect_function):
        label = QLabel(f'{name}: {current_value}')
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue(current_value)
        slider.valueChanged.connect(connect_function)
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
        webbrowser.open('https://www.hircoir.eu.org/onnx-tts/')

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
                file_url = base_url + file_path
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
        self.setStyleSheet('''
            QDialog {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
            }
            QListWidget {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                margin: 5px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        ''')

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Search model...')
        self.search_bar.textChanged.connect(self.filter_models)
        layout.addWidget(self.search_bar)

        self.model_list = QListWidget()
        self.model_list.addItems(list(voices_data.keys()))
        layout.addWidget(self.model_list)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.download_button = QPushButton('Download Selected Model')
        self.download_button.clicked.connect(self.download_selected_model)
        layout.addWidget(self.download_button)

        self.download_thread = None

    def filter_models(self, text):
        self.model_list.clear()
        filtered_models = [model for model in voices_data.keys() if text.lower() in model.lower()]
        self.model_list.addItems(filtered_models)

    def download_selected_model(self):
        selected_items = self.model_list.selectedItems()
        if selected_items:
            selected_key = selected_items[0].text()
            if selected_key in voices_data:
                model_info = voices_data[selected_key]
                files = model_info["files"]
                self.download_thread = DownloadModelThread(selected_key, files)
                self.download_thread.progress_updated.connect(self.update_progress)
                self.download_thread.download_finished.connect(self.download_finished)
                self.download_thread.start()
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.download_button.setEnabled(False)
            else:
                QMessageBox.critical(self, "Error", "Model not found.")
        else:
            QMessageBox.warning(self, "Warning", "Please select a model to download.")

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def download_finished(self, model_key):
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.parent().update_model_spinner()
        self.parent().audio_label.setText(f'Model {model_key} downloaded successfully.')

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
        self.download_dialog = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ONNX - Text to Speech Converter')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet('''
            QWidget {
                background-color: #2E2E2E;
                color: white;
                font-family: Arial, sans-serif;
            }
            QLabel {
                font-size: 18px;
            }
            QTextEdit, QComboBox {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                font-size: 16px;
            }
            QComboBox {
                text-align: center;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                margin: 5px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        ''')

        layout = QVBoxLayout()

        title = QLabel('Text to Audio Converter')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 30px; font-weight: bold; margin-bottom: 20px;')
        layout.addWidget(title)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText('Enter text here')
        self.text_input.textChanged.connect(self.on_text_changed)
        self.text_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_input.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.text_input, 1)

        model_layout = QHBoxLayout()
        self.model_spinner = QComboBox()
        self.model_spinner.setStyleSheet('''
            QComboBox {
                text-align-last: center;
                padding-left: 15px;
                padding-right: 15px;
            }
        ''')
        self.model_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_spinner.setFixedHeight(40)
        self.model_spinner.addItem("Select a model")
        self.update_model_spinner()
        model_layout.addWidget(self.model_spinner)

        self.download_button = QPushButton('Download Model')
        self.download_button.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                margin: 5px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        ''')
        self.download_button.clicked.connect(self.show_download_dialog)
        model_layout.addWidget(self.download_button)

        # Disable the download button if there is no internet connection or the JSON cannot be accessed
        if not voices_data:
            self.download_button.setEnabled(False)

        layout.addLayout(model_layout)

        button_layout = QHBoxLayout()
        self.convert_button = QPushButton('Generate Audio')
        self.convert_button.clicked.connect(self.convert_text)
        button_layout.addWidget(self.convert_button)

        self.save_button = QPushButton('Save Audio')
        self.save_button.clicked.connect(self.save_audio)
        button_layout.addWidget(self.save_button)

        self.settings_button = QPushButton('Model Settings')
        self.settings_button.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_button)

        layout.addLayout(button_layout)

        self.audio_label = QLabel('Audio will be played here')
        self.audio_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.audio_label)

        self.audio_controls = QHBoxLayout()
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(play_icon_path))
        self.play_button.clicked.connect(self.play_audio)
        self.audio_controls.addWidget(self.play_button)

        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon(pause_icon_path))
        self.pause_button.clicked.connect(self.pause_audio)
        self.audio_controls.addWidget(self.pause_button)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self.set_position)
        self.slider.sliderPressed.connect(self.pause_audio)
        self.slider.sliderReleased.connect(self.play_audio)
        self.audio_controls.addWidget(self.slider)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.audio_controls.addWidget(QLabel('Volume'))
        self.audio_controls.addWidget(self.volume_slider)

        self.duration_label = QLabel('00:00 / 00:00')
        self.audio_controls.addWidget(self.duration_label)

        layout.addLayout(self.audio_controls)

        self.setLayout(layout)

        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)

    def update_model_spinner(self):
        self.model_spinner.clear()
        self.model_spinner.addItem("Select a model")
        downloaded_models = [f for f in os.listdir(model_folder) if f.endswith('.onnx')]
        self.model_spinner.addItems([os.path.splitext(model)[0] for model in downloaded_models])

    def show_download_dialog(self):
        if self.download_dialog is None:
            self.download_dialog = DownloadModelDialog(self)
            self.download_dialog.finished.connect(self.on_download_dialog_finished)
            self.download_dialog.show()
            self.download_button.setEnabled(False)

    def on_download_dialog_finished(self):
        self.download_dialog = None
        self.download_button.setEnabled(True)

    def convert_text(self):
        text = self.text_input.toPlainText()
        model_name = self.model_spinner.currentText()
        if model_name == "Select a model":
            QMessageBox.warning(self, 'Error', 'Please select a model before generating audio.')
            return
        random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.wav'
        output_file = os.path.join(temp_audio_folder, random_name)

        for file in os.listdir(temp_audio_folder):
            if file.endswith('.wav'):
                os.remove(os.path.join(temp_audio_folder, file))

        if os.path.isfile(piper_binary_path) and model_folder is not None:
            model_path = os.path.join(model_folder, model_name + '.onnx')
            if os.path.isfile(model_path):
                self.audio_label.setText('Generating audio...')
                self.conversion_thread = ConvertTextToSpeechThread(
                    text, model_path, output_file,
                    self.speaker, self.noise_scale, self.length_scale, self.noise_w, self.sentence_silence
                )
                self.conversion_thread.conversion_done.connect(self.handle_conversion_done)
                self.conversion_thread.start()
            else:
                self.audio_label.setText('Model not found.')
        else:
            self.audio_label.setText('Piper binary not found or no model folder selected.')

    def handle_conversion_done(self, output_file):
        if output_file:
            self.audio_file = output_file
            self.audio_label.setText('Audio generated')
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(output_file)))
            self.player.setVolume(self.volume)
            self.play_audio()
        else:
            self.audio_label.setText('Could not generate audio.')

    def save_audio(self):
        if self.audio_file:
            save_path, _ = QFileDialog.getSaveFileName(self, 'Save audio file', '', 'Audio Files (*.wav)')
            if save_path:
                os.rename(self.audio_file, save_path)
                self.audio_file = save_path
                QMessageBox.information(self, 'File Saved', 'The audio file has been saved successfully')

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

    def show_settings(self):
        self.settings_button.setEnabled(False)
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.finished.connect(lambda: self.settings_button.setEnabled(True))
        self.settings_dialog.show()

    def on_text_changed(self):
        if self.processing_text:
            return
        self.processing_text = True
        if self.remove_style_enabled:
            self.text_input.setPlainText(self.text_input.toPlainText())
        self.processing_text = False

    def show_context_menu(self, pos):
        context_menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.text_input.copy)
        context_menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.text_input.paste)
        context_menu.addAction(paste_action)

        paste_without_formatting_action = QAction("Paste without formatting", self)
        paste_without_formatting_action.triggered.connect(self.paste_without_formatting)
        context_menu.addAction(paste_without_formatting_action)

        context_menu.exec_(self.text_input.mapToGlobal(pos))

    def paste_without_formatting(self):
        cursor = self.text_input.textCursor()
        mime_data = QApplication.clipboard().mimeData()
        if mime_data.hasText():
            cursor.insertText(mime_data.text())
        self.text_input.setTextCursor(cursor)

if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    tts_app = TTSApp()
    tts_app.setWindowTitle('Text to Speech Converter')
    tts_app.setWindowIcon(QIcon(icon_path))
    tts_app.show()
    app.exec_()
