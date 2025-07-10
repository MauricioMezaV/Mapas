from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session
import os
import shutil
import uuid
from kml_processor import process_kml
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave-insegura-solo-para-dev')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

UPLOAD_FOLDER = 'uploads'
OUTPUTS_ROOT = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUTS_ROOT, exist_ok=True)

def allowed_file(filename):
    # Valida extensión y que no tenga doble extensión
    return (
        '.' in filename and 
        filename.rsplit('.', 1)[1].lower() == 'kml' and 
        filename.lower().endswith('.kml')
    )

def clean_old_outputs(directorio, horas=1, user_id=None):
    ahora = time.time()
    for nombre in os.listdir(directorio):
        ruta = os.path.join(directorio, nombre)
        if os.path.isdir(ruta):
            # Elimina carpetas si son viejas o corresponden al usuario actual
            if (ahora - os.path.getmtime(ruta) > horas * 3600) or (user_id and nombre == user_id):
                shutil.rmtree(ruta)
        elif os.path.isfile(ruta):
            # Elimina archivos si son viejos o corresponden al usuario actual
            if (ahora - os.path.getmtime(ruta) > horas * 3600) or (user_id and nombre.startswith(user_id)):
                os.remove(ruta)

@app.route('/', methods=['GET', 'POST'])
def index():
    files = []
    success = None
    error = None

    if request.method == 'POST':
        # Limpia outputs viejos antes de procesar
        clean_old_outputs(OUTPUTS_ROOT, horas=1)
        # Limpia la visualización de archivos previos
        files = []
        success = None
        error = None

        file = request.files.get('kmlfile')
        if file and allowed_file(file.filename):
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
            output_dir = os.path.join(OUTPUTS_ROOT, user_id)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            # Guarda el archivo con un nombre seguro
            filename = f"{user_id}.kml"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            try:
                process_kml(filepath, output_dir)
                files = os.listdir(output_dir)
                if files:
                    success = "Procesamiento completado. Descarga tus archivos:"
                else:
                    error = "No se generaron archivos de salida."
            except Exception as e:
                error = f"Ocurrió un error al procesar el archivo: {str(e)}"
        else:
            error = "Por favor, sube un archivo KML válido."
    # Si es GET o POST, siempre se renderiza con la lista actual de archivos (vacía si es un nuevo POST)
    return render_template('index.html', files=files, success=success, error=error)

@app.route('/outputs/<filename>')
def download_file(filename):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    output_dir = os.path.join(OUTPUTS_ROOT, user_id)
    # Solo permite descargar archivos de la carpeta del usuario
    if filename not in os.listdir(output_dir):
        return redirect(url_for('index'))
    return send_from_directory(output_dir, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)