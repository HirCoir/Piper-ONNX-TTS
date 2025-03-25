# Piper-ONNX-TTS

![Image](Photo.jpg)

**Piper-ONNX-TTS** es una aplicación de conversión de texto a voz (TTS) basada en el modelo **Piper** y **ONNX**. Esta herramienta permite generar audio a partir de texto utilizando modelos de voz preentrenados, con una interfaz gráfica intuitiva y fácil de usar.

## Características Principales

- **Conversión de Texto a Voz**: Convierte cualquier texto en audio utilizando modelos de voz de alta calidad.
- **Interfaz Gráfica Amigable**: Diseño moderno y fácil de usar, con controles intuitivos para la reproducción y ajustes de audio.
- **Personalización de Voz**: Ajusta parámetros como el hablante, la escala de ruido, la escala de longitud, el ruido W y el silencio entre frases para personalizar la salida de audio.
- **Descarga de Modelos**: Descarga nuevos modelos de voz directamente desde la aplicación.
- **Reproducción de Audio**: Reproduce el audio generado directamente en la aplicación, con controles de reproducción, pausa y volumen.
- **Guardado de Audio**: Guarda el audio generado en formato WAV para su uso posterior.
- **Compatibilidad con Múltiples Idiomas**: Soporta una amplia variedad de idiomas y voces, gracias a los modelos disponibles en **Piper**.
- **Configuración Avanzada**: Ajustes avanzados para personalizar la calidad y el estilo de la voz generada.
- **Temas de Interfaz**: Cambia entre temas claros y oscuros para una mejor experiencia visual.
- **Gestión de Modelos**: Administra los modelos descargados, incluyendo la eliminación de modelos no deseados.
- **Búsqueda de Texto**: Funcionalidad para buscar y resaltar texto dentro del área de entrada.
- **Inserción de Silencios**: Añade silencios personalizados entre frases.
- **Integración de FFmpeg**: Uso de FFmpeg para la generación y concatenación de archivos de audio.

## Requisitos

- **Piper**: Asegúrate de tener el binario de **Piper** (`piper.exe`) descargado y colocado en la carpeta del proyecto.
- **Python 3.10 o superior**: La aplicación está desarrollada en Python y requiere la instalación de varias dependencias.
- **Dependencias**: Asegúrate de instalar las dependencias necesarias utilizando `pip install -r requirements.txt`.
- **FFmpeg**: La aplicación requiere FFmpeg para la manipulación de archivos de audio. Asegúrate de tener `ffmpeg.exe` en la carpeta del proyecto.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/HirCoir/Piper-ONNX-TTS.git
   ```
2. Navega a la carpeta del proyecto:
   ```bash
   cd Piper-ONNX-TTS
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Descarga el binario de [**Piper**](https://github.com/rhasspy/piper/releases) y colócalo en la carpeta del proyecto.
5. Asegúrate de tener `ffmpeg.exe` en la carpeta del proyecto.

## Uso

1. Ejecuta la aplicación:
   ```bash
   python main.py
   ```
2. Introduce el texto que deseas convertir en el cuadro de texto.
3. Selecciona un modelo de voz de la lista desplegable.
4. Ajusta los parámetros de la voz si es necesario.
5. Haz clic en "Generar audio" para convertir el texto en audio.
6. Reproduce el audio generado o guárdalo en tu dispositivo.

## Descargas

Puedes encontrar una versión compilada del proyecto en la sección de [Releases](https://github.com/HirCoir/Piper-ONNX-TTS/releases).

## Contribuciones

¡Las contribuciones son bienvenidas! Si deseas mejorar el proyecto, por favor abre un **Pull Request** o un **Issue** en el repositorio.

## Licencia

Este proyecto está bajo la licencia **MIT**.

## Agradecimientos

- **Piper**: Gracias al equipo de [**Piper**](https://github.com/rhasspy/piper) por proporcionar los modelos de voz y el binario necesario.
- **ONNX**: Gracias a [**ONNX**](https://github.com/onnx/onnx) por proporcionar el marco de trabajo para la inferencia de modelos.

---

### ¡Apoya el Proyecto!

Si encuentras útil este proyecto, considera hacer una donación. Tu apoyo ayuda a mantener y mejorar esta herramienta. ¡Gracias!

[![Donar con PayPal](https://www.paypalobjects.com/es_XC/i/btn/btn_donate_LG.gif)](https://paypal.me/hircoir)
