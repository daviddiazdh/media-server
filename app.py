from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory, jsonify
import shutil
import os
import subprocess
import psutil
import threading
import time
import logging

# Crear carpeta de logs si no existe
os.makedirs('logs', exist_ok=True)

# Configuración básica de logging
logging.basicConfig(
    filename='logs/server.log',  # archivo donde se guardarán los logs
    level=logging.INFO,           # nivel mínimo de log
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mkv'}

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Servidor Familia Díaz</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='servidor_casa.css') }}">
</head>
<body>
    <nav class='side-bar-nav'>
        <a href="{{ url_for('upload_file', path='') }}" class='title'>
            <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='white' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-folder'><path d='M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'/></svg>
            <h1>Inicio</h1>
        </a>
        <div class='options-container'>
            <a href="{{ url_for('upload_file', path='') }}" class='option-side-bar'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-home'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>
                <p>Inicio</p>
            </a>
            <a href="{{ url_for('upload_file', path='documentos') }}" class='option-side-bar'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-file-text'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/><polyline points='10 9 9 9 8 9'/></svg>
                <p>Documentos</p>
            </a>
            <a href="{{ url_for('upload_file', path='imagenes') }}" class='option-side-bar'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-image'><rect x='3' y='3' width='18' height='18' rx='2' ry='2'/><circle cx='8.5' cy='8.5' r='1.5'/><polyline points='21 15 16 10 5 21'/></svg>
                <p>Imágenes</p>
            </a>
            <a href="{{ url_for('upload_file', path='videos') }}" class='option-side-bar'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-video'><polygon points='23 7 16 12 23 17 23 7'/><rect x='1' y='5' width='15' height='14' rx='2' ry='2'/></svg>
                <p>Videos</p>
            </a>
        </div>
        <div class='storage-box'>
            <div class='storage-title-svg'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-cloud'><path d='M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z'/></svg>
                <p>Almacenamiento</p>
            </div>
            <div class='storage-bar-box'>
                <div class='storage-bar' style="width: {{ (used_gb / total_gb)*100 }}%;"> </div>
            </div>
            <span class='storage-availability-display-message'>
                {{ '%.2f' % used_gb }} GB usados de {{ '%.2f' % total_gb }} GB ({{ '%.1f' % ((used_gb / total_gb)*100) }}%)
            </span>
        </div>
    </nav>
    <div class='main-section'>
        <div class='header-box'>
            <div class='options-container'>
                <svg xmlns='http://www.w3.org/2000/svg' width='24px' height='24px' viewBox='0 0 28 28' fill='none'><path clip-rule='evenodd' d='M14 20C17.3137 20 20 17.3137 20 14C20 10.6863 17.3137 8 14 8C10.6863 8 8 10.6863 8 14C8 17.3137 10.6863 20 14 20ZM18 14C18 16.2091 16.2091 18 14 18C11.7909 18 10 16.2091 10 14C10 11.7909 11.7909 10 14 10C16.2091 10 18 11.7909 18 14Z' fill='#000000' fill-rule='evenodd'/><path clip-rule='evenodd' d='M0 12.9996V14.9996C0 16.5478 1.17261 17.822 2.67809 17.9826C2.80588 18.3459 2.95062 18.7011 3.11133 19.0473C2.12484 20.226 2.18536 21.984 3.29291 23.0916L4.70712 24.5058C5.78946 25.5881 7.49305 25.6706 8.67003 24.7531C9.1044 24.9688 9.55383 25.159 10.0163 25.3218C10.1769 26.8273 11.4511 28 12.9993 28H14.9993C16.5471 28 17.8211 26.8279 17.9821 25.3228C18.4024 25.175 18.8119 25.0046 19.2091 24.8129C20.3823 25.6664 22.0344 25.564 23.0926 24.5058L24.5068 23.0916C25.565 22.0334 25.6674 20.3813 24.814 19.2081C25.0054 18.8113 25.1757 18.4023 25.3234 17.9824C26.8282 17.8211 28 16.5472 28 14.9996V12.9996C28 11.452 26.8282 10.1782 25.3234 10.0169C25.1605 9.55375 24.9701 9.10374 24.7541 8.66883C25.6708 7.49189 25.5882 5.78888 24.5061 4.70681L23.0919 3.29259C21.9846 2.18531 20.2271 2.12455 19.0485 3.1103C18.7017 2.94935 18.3459 2.80441 17.982 2.67647C17.8207 1.17177 16.5468 0 14.9993 0H12.9993C11.4514 0 10.1773 1.17231 10.0164 2.6775C9.60779 2.8213 9.20936 2.98653 8.82251 3.17181C7.64444 2.12251 5.83764 2.16276 4.70782 3.29259L3.2936 4.7068C2.16377 5.83664 2.12352 7.64345 3.17285 8.82152C2.98737 9.20877 2.82199 9.60763 2.67809 10.0167C1.17261 10.1773 0 11.4515 0 12.9996ZM15.9993 3C15.9993 2.44772 15.5516 2 14.9993 2H12.9993C12.447 2 11.9993 2.44772 11.9993 3V3.38269C11.9993 3.85823 11.6626 4.26276 11.2059 4.39542C10.4966 4.60148 9.81974 4.88401 9.18495 5.23348C8.76836 5.46282 8.24425 5.41481 7.90799 5.07855L7.53624 4.70681C7.14572 4.31628 6.51256 4.31628 6.12203 4.7068L4.70782 6.12102C4.31729 6.51154 4.31729 7.14471 4.70782 7.53523L5.07958 7.90699C5.41584 8.24325 5.46385 8.76736 5.23451 9.18395C4.88485 9.8191 4.6022 10.4963 4.39611 11.2061C4.2635 11.6629 3.85894 11.9996 3.38334 11.9996H3C2.44772 11.9996 2 12.4474 2 12.9996V14.9996C2 15.5519 2.44772 15.9996 3 15.9996H3.38334C3.85894 15.9996 4.26349 16.3364 4.39611 16.7931C4.58954 17.4594 4.85042 18.0969 5.17085 18.6979C5.39202 19.1127 5.34095 19.6293 5.00855 19.9617L4.70712 20.2632C4.3166 20.6537 4.3166 21.2868 4.70712 21.6774L6.12134 23.0916C6.51186 23.4821 7.14503 23.4821 7.53555 23.0916L7.77887 22.8483C8.11899 22.5081 8.65055 22.4633 9.06879 22.7008C9.73695 23.0804 10.4531 23.3852 11.2059 23.6039C11.6626 23.7365 11.9993 24.1411 11.9993 24.6166V25C11.9993 25.5523 12.447 26 12.9993 26H14.9993C15.5516 26 15.9993 25.5523 15.9993 25V24.6174C15.9993 24.1418 16.3361 23.7372 16.7929 23.6046C17.5032 23.3985 18.1809 23.1157 18.8164 22.7658C19.233 22.5365 19.7571 22.5845 20.0934 22.9208L20.2642 23.0916C20.6547 23.4821 21.2879 23.4821 21.6784 23.0916L23.0926 21.6774C23.4831 21.2868 23.4831 20.6537 23.0926 20.2632L22.9218 20.0924C22.5855 19.7561 22.5375 19.232 22.7669 18.8154C23.1166 18.1802 23.3992 17.503 23.6053 16.7931C23.7379 16.3364 24.1425 15.9996 24.6181 15.9996H25C25.5523 15.9996 26 15.5519 26 14.9996V12.9996C26 12.4474 25.5523 11.9996 25 11.9996H24.6181C24.1425 11.9996 23.7379 11.6629 23.6053 11.2061C23.3866 10.4529 23.0817 9.73627 22.7019 9.06773C22.4643 8.64949 22.5092 8.11793 22.8493 7.77781L23.0919 7.53523C23.4824 7.14471 23.4824 6.51154 23.0919 6.12102L21.6777 4.7068C21.2872 4.31628 20.654 4.31628 20.2635 4.7068L19.9628 5.00748C19.6304 5.33988 19.1137 5.39096 18.6989 5.16979C18.0976 4.84915 17.4596 4.58815 16.7929 4.39467C16.3361 4.2621 15.9993 3.85752 15.9993 3.38187V3Z' fill='#000000' fill-rule='evenodd'/></svg>
            </div>
        </div>
        <div class='media-body'>
            <div class='drag-n-drop-box'>
                <div class='file-input-description-container'>
                    <form class="file_box" id="uploadForm" enctype="multipart/form-data">
                        <label for="file-upload" class="upload_file transparent_blue_bg"> + </label>
                        <input id="file-upload" type="file" name="file" multiple>
                        <p class="input_box_title">Sube un archivo</p>
                    </form>
                </div>
                <form class='dir-input-description-container' method="post" action="{{ url_for('create_folder', path=path) }}">
                    <div class="file_box">
                        <button class="upload_file transparent_yellow_bg" type="submit"> + </button>
                        <p class="input_box_title">Crea una carpeta</p>
                    </div>
                    <input type="text" name="foldername" placeholder="Nombre de la carpeta" required>
                </form>
            </div>
            <div id="globalProgressContainer">
                <div id="globalProgressBar"></div>
            </div>
            <ul id="uploadStatus"></ul>
            <script>
            document.getElementById('file-upload').addEventListener('change', async function () {
            const files = this.files;
            const totalFiles = files.length;
            const path = window.location.pathname;

            const globalBar = document.getElementById('globalProgressBar');
            const uploadStatus = document.getElementById('uploadStatus');

            uploadStatus.textContent = '';
            globalBar.style.width = '0%';

            let uploadedCount = 0;

            for (let i = 0; i < totalFiles; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                try {
                await new Promise((resolve, reject) => {
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', path, true);

                    xhr.onload = function () {
                    if (xhr.status === 200 || xhr.status === 302) {
                        uploadedCount++;
                        const percent = (uploadedCount / totalFiles) * 100;
                        globalBar.style.width = `${percent.toFixed(1)}%`;
                        uploadStatus.innerText = `Subido ${uploadedCount} de ${totalFiles} archivos`;
                        resolve();
                    } else {
                        uploadStatus.innerText += `\n❌ Error al subir ${file.name}`;
                        reject();
                    }
                    };

                    xhr.onerror = function () {
                    uploadStatus.innerText += `\n❌ Error al subir ${file.name}`;
                    reject();
                    };

                    xhr.send(formData);
                });
                } catch (err) {
                // El error ya se mostró
                }
            }

            // Al terminar
            if (uploadedCount === totalFiles) {
                uploadStatus.innerText += `\n✅ Todos los archivos fueron subidos correctamente`;
                setTimeout(() => location.reload(), 1500);
            }
            });
            </script>
            <div class='media-container'>
                <h2>Carpetas</h2>
                <div class='media-files'>
                    {% for folder in folders %}
                        <a style="position: relative;" class='dir-option' href="{{ url_for('upload_file', path=path ~ '/' ~ folder if path else folder) }}">
                            
                            <form action="{{ url_for('delete_file', file_path=(path + '/' + folder) if path else folder) }}"
                                method="post"
                                style="position: absolute; top: 50%; right: 5px; transform: translateY(-50%);">
                                <button type="submit"
                                        onclick="return confirm('¿Estás seguro de que deseas eliminar esta carpeta?')"
                                        style="background: transparent; border: none; cursor: pointer;">
                                    ❌
                                </button>
                            </form>

                            <svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='white' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-folder'><path d='M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'/></svg>
                            <span>{{folder}}</span>
                        </a>
                    {% endfor %}
                </div>
            </div>
            </div>
            <div class='media-container'>
                <h2>Archivos</h2>
                <div class='media-files'>
                    {% for file in files %}
                        <div class="media_item" style="position: relative;">
                            {% if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')) %}

                                <a style="position: relative;" class='dir-option' href="{{ url_for('uploaded_file', filename=(path ~ '/' if path else '') ~ file) }}">
                                    
                                    <form action="{{ url_for('delete_file', file_path=path + '/' + file if path else file) }}"
                                        method="post"
                                        style="position: absolute; top: 50%; right: 5px; transform: translateY(-50%);">
                                        <button type="submit" onclick="return confirm('¿Estás seguro de que deseas eliminar esta imagen?')" style="background: transparent; border: none; cursor: pointer;">
                                            ❌
                                        </button>
                                    </form>

                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path fill-rule="evenodd" clip-rule="evenodd" d="M3.17157 3.17157C2 4.34314 2 6.22876 2 9.99999V14C2 17.7712 2 19.6568 3.17157 20.8284C4.34315 22 6.22876 22 10 22H14C17.7712 22 19.6569 22 20.8284 20.8284C22 19.6569 22 17.7712 22 14V14V9.99999C22 7.16065 22 5.39017 21.5 4.18855V17C20.5396 17 19.6185 16.6185 18.9393 15.9393L18.1877 15.1877C17.4664 14.4664 17.1057 14.1057 16.6968 13.9537C16.2473 13.7867 15.7527 13.7867 15.3032 13.9537C14.8943 14.1057 14.5336 14.4664 13.8123 15.1877L13.6992 15.3008C13.1138 15.8862 12.8212 16.1788 12.5102 16.2334C12.2685 16.2758 12.0197 16.2279 11.811 16.0988C11.5425 15.9326 11.3795 15.5522 11.0534 14.7913L11 14.6667C10.2504 12.9175 9.87554 12.0429 9.22167 11.7151C8.89249 11.5501 8.52413 11.4792 8.1572 11.5101C7.42836 11.5716 6.75554 12.2445 5.40989 13.5901L3.5 15.5V2.88739C3.3844 2.97349 3.27519 3.06795 3.17157 3.17157Z" fill="#222222"></path> <path d="M3 10C3 8.08611 3.00212 6.75129 3.13753 5.74416C3.26907 4.76579 3.50966 4.2477 3.87868 3.87868C4.2477 3.50966 4.76579 3.26907 5.74416 3.13753C6.75129 3.00212 8.08611 3 10 3H14C15.9139 3 17.2487 3.00212 18.2558 3.13753C19.2342 3.26907 19.7523 3.50966 20.1213 3.87868C20.4903 4.2477 20.7309 4.76579 20.8625 5.74416C20.9979 6.75129 21 8.08611 21 10V14C21 15.9139 20.9979 17.2487 20.8625 18.2558C20.7309 19.2342 20.4903 19.7523 20.1213 20.1213C19.7523 20.4903 19.2342 20.7309 18.2558 20.8625C17.2487 20.9979 15.9139 21 14 21H10C8.08611 21 6.75129 20.9979 5.74416 20.8625C4.76579 20.7309 4.2477 20.4903 3.87868 20.1213C3.50966 19.7523 3.26907 19.2342 3.13753 18.2558C3.00212 17.2487 3 15.9139 3 14V10Z" stroke="#222222" stroke-width="2"></path> <circle cx="15" cy="9" r="2" fill="#222222"></circle> </g></svg>
                                    <span>{{file|truncate(25, True, '...')}}</span>
                                </a>

                            {% elif file.endswith(('.mp4', '.mkv')) %}
                                <a style="position: relative;" class='dir-option' href="{{ url_for('uploaded_file', filename=(path ~ '/' if path else '') ~ file) }}">
                                    
                                    <form action="{{ url_for('delete_file', file_path=path + '/' + file if path else file) }}"
                                        method="post"
                                        style="position: absolute; top: 50%; right: 5px; transform: translateY(-50%);">
                                        <button type="submit" onclick="return confirm('¿Estás seguro de que deseas eliminar esta imagen?')" style="background: transparent; border: none; cursor: pointer;">
                                            ❌
                                        </button>
                                    </form>

                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path fill-rule="evenodd" clip-rule="evenodd" d="M8 10.4656V13.5344C8 15.6412 10.2299 16.4543 11.6609 15.7205L14.6534 14.1861C16.4489 13.2655 16.4488 10.7345 14.6534 9.81391L11.6609 8.27949C10.2299 7.54573 8 8.3588 8 10.4656ZM10 13.5344C10 13.8889 10.4126 14.113 10.7484 13.9408L13.7409 12.4064C14.0864 12.2293 14.0864 11.7707 13.7409 11.5936L10.7484 10.0592C10.4126 9.88702 10 10.1111 10 10.4656V13.5344Z" fill="#000000"></path> <path fill-rule="evenodd" clip-rule="evenodd" d="M7 2C4.23858 2 2 4.23858 2 7V17C2 19.7614 4.23858 22 7 22H17C19.7614 22 22 19.7614 22 17V7C22 4.23858 19.7614 2 17 2H7ZM4 7C4 5.34315 5.34315 4 7 4H17C18.6569 4 20 5.34315 20 7V17C20 18.6569 18.6569 20 17 20H7C5.34315 20 4 18.6569 4 17V7Z" fill="#000000"></path> </g></svg>
                                    <span>{{file|truncate(25, True, '...')}}</span>
                                </a>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            </div>

            <script>
                async function updateStatus() {
                    const res = await fetch("/status");
                    const data = await res.json();

                    document.getElementById("cpu").textContent = data.cpu;
                    document.getElementById("ram").textContent = data.ram;
                    document.getElementById("load").textContent = data.load.join(", ");
                }

                setInterval(updateStatus, 4000); // Actualiza cada 6s
                updateStatus();
            </script>
        </div>
    </div>
</body>
</html>
'''


@app.route('/disk-raw')
def disk_raw():
    try:
        with open('../metrics_disk.csv', 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except FileNotFoundError:
        return "metrics_disk.csv not found", 404


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_join(base, *paths):
    final_path = os.path.normpath(os.path.join(base, *paths))
    if not os.path.abspath(final_path).startswith(os.path.abspath(base)):
        raise ValueError("Ruta no permitida")
    return final_path

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/create-folder', defaults={'path': ''}, methods=['POST'])
@app.route('/<path:path>/create-folder', methods=['POST'])
def create_folder(path):
    foldername = request.form.get('foldername')
    current_path = safe_join(app.config['UPLOAD_FOLDER'], path)
    if foldername:
        folder_path = os.path.join(current_path, foldername)
        os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Carpeta creada: {folder_path}")
    return redirect(url_for('upload_file', path=path))

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def upload_file(path):
    current_path = safe_join(app.config['UPLOAD_FOLDER'], path)
    os.makedirs(current_path, exist_ok=True)

    if request.method == 'POST':
        files = request.files.getlist('file')
        for file in files:
            if file and allowed_file(file.filename):
                filename = file.filename
                filepath = os.path.join(current_path, filename)
                file.save(filepath)
                logging.info(f"Archivo subido: {filepath}")

                # Si es video, generar miniatura
                if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    thumbnail_path = os.path.join(current_path, filename.rsplit('.', 1)[0] + '.jpg')
                    try:
                        subprocess.run([
                            'ffmpeg',
                            '-i', filepath,
                            '-ss', '00:00:01.000',
                            '-vframes', '1',
                            thumbnail_path
                        ], check=True)
                        logging.info(f"Miniatura generada: {thumbnail_path}")
                    except subprocess.CalledProcessError as e:
                        logging.error(f'Error generando miniatura de {filepath}: {e}')
        return redirect(request.url)

    items = os.listdir(current_path)
    files = [f for f in items if os.path.isfile(os.path.join(current_path, f))]
    folders = [f for f in items if os.path.isdir(os.path.join(current_path, f))]

    rel_path = path.strip('/')

    # Obtener info de disco raíz
    total, used, free = shutil.disk_usage('/')

    # Pasar a MB o GB para mostrar más legible
    total_gb = total / (1024**3)
    used_gb = used / (1024**3)
    free_gb = free / (1024**3)

    return render_template_string(
        HTML,
        files=files,
        folders=folders,
        path=rel_path,
        total_gb=total_gb,
        used_gb=used_gb,
        free_gb=free_gb
    )

def generate_thumbnail(video_path, thumbnail_path):
    try:
        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-ss", "00:00:01.000",
            "-vframes", "1",
            "-q:v", "2",
            thumbnail_path
        ], check=True)
    except subprocess.CalledProcessError:
        print("Error al generar la miniatura")

@app.route('/delete-file/<path:file_path>', methods=['POST'])
def delete_file(file_path):
    full_path = safe_join(app.config['UPLOAD_FOLDER'], file_path)
    if os.path.exists(full_path):
        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
                logging.info(f"Archivo eliminado: {full_path}")
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
                logging.info(f"Carpeta eliminada: {full_path}")
        except Exception as e:
            logging.error(f"Error eliminando {full_path}: {e}")
    return redirect(request.referrer or url_for('upload_file'))



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
