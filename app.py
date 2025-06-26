from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
from kml_processor import process_kml

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['kmlfile']
        if file and file.filename.endswith('.kml'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            process_kml(filepath)
            return redirect(url_for('download'))
    return render_template('index.html')

@app.route('/download')
def download():
    files = os.listdir(OUTPUT_FOLDER)
    return render_template('download.html', files=files)

@app.route('/outputs/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)