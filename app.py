from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session
import os
import shutil
import uuid
from kml_processor import process_kml
import time

app = Flask(__name__)
app.secret_key = 'algo-muy-seguro'  # Necesario para usar sesiones

UPLOAD_FOLDER = 'uploads'
OUTPUTS_ROOT = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUTS_ROOT, exist_ok=True)

def clean_old_outputs(directorio, horas=1):
    ahora = time.time()
    for nombre_carpeta in os.listdir(directorio):
        ruta_carpeta = os.path.join(directorio, nombre_carpeta)
        if os.path.isdir(ruta_carpeta):
            # Si la carpeta es más vieja que 'horas'
            if ahora - os.path.getmtime(ruta_carpeta) > horas * 3600:
                shutil.rmtree(ruta_carpeta)

@app.route('/', methods=['GET', 'POST'])
def index():
    files = []
    success = None
    error = None
    output_filename = None

    if request.method == 'POST':
        clean_old_outputs(OUTPUTS_ROOT, horas=24)
        file = request.files['kmlfile']
        if file and file.filename.endswith('.kml'):
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
            output_dir = os.path.join(OUTPUTS_ROOT, user_id)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            process_kml(filepath, output_dir)
            files = os.listdir(output_dir)
            if files:
                success = "Procesamiento completado. Descarga tus archivos:"
            else:
                error = "No se generaron archivos de salida."
        else:
            error = "Por favor, sube un archivo KML válido."
    return render_template('index.html', files=files, success=success, error=error)

@app.route('/outputs/<filename>')
def download_file(filename):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    output_dir = os.path.join(OUTPUTS_ROOT, user_id)
    return send_from_directory(output_dir, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)