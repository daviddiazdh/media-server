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

                                <a style="position: relative;" class='media-option' href="{{ url_for('uploaded_file', filename=(path ~ '/' if path else '') ~ file) }}">
                                    
                                    <form action="{{ url_for('delete_file', file_path=path + '/' + file if path else file) }}"
                                        method="post"
                                        style="position: absolute; top: 50%; right: 5px; transform: translateY(-50%);">
                                        <button type="submit" onclick="return confirm('¿Estás seguro de que deseas eliminar esta imagen?')" style="background: transparent; border: none; cursor: pointer;">
                                            ❌
                                        </button>
                                    </form>

                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M3 11C3 7.22876 3 5.34315 4.17157 4.17157C5.34315 3 7.22876 3 11 3H13C16.7712 3 18.6569 3 19.8284 4.17157C21 5.34315 21 7.22876 21 11V13C21 16.7712 21 18.6569 19.8284 19.8284C18.6569 21 16.7712 21 13 21H11C7.22876 21 5.34315 21 4.17157 19.8284C3 18.6569 3 16.7712 3 13V11Z" stroke="#33363F" stroke-width="2"></path> <path fill-rule="evenodd" clip-rule="evenodd" d="M18.9997 13.5854L18.9794 13.5651C18.5898 13.1754 18.2537 12.8393 17.9536 12.5864C17.6367 12.3193 17.2917 12.0845 16.8665 11.9562C16.3014 11.7857 15.6986 11.7857 15.1335 11.9562C14.7083 12.0845 14.3633 12.3193 14.0464 12.5864C13.7463 12.8393 13.4102 13.1754 13.0206 13.5651L12.9921 13.5936C12.6852 13.9004 12.5046 14.0795 12.3645 14.1954L12.3443 14.2118L12.3317 14.1891C12.2447 14.0295 12.1435 13.7961 11.9726 13.3972L11.9191 13.2726L11.8971 13.2211L11.897 13.221C11.5411 12.3904 11.2422 11.693 10.9464 11.1673C10.6416 10.6257 10.2618 10.1178 9.66982 9.82106C9.17604 9.57352 8.6235 9.46711 8.07311 9.51356C7.41323 9.56924 6.87197 9.89977 6.38783 10.2894C5.98249 10.6157 5.52754 11.0598 5 11.5859V12.9999C5 13.5166 5.0003 13.9848 5.00308 14.411L6.117 13.2971C6.80615 12.6079 7.26639 12.1497 7.64186 11.8475C8.01276 11.5489 8.17233 11.5123 8.24128 11.5065C8.42475 11.491 8.60893 11.5265 8.77352 11.609C8.83539 11.64 8.96994 11.7333 9.20344 12.1482C9.43981 12.5682 9.69693 13.1646 10.0809 14.0605L10.1343 14.1851L10.1506 14.2232C10.2995 14.5707 10.4378 14.8936 10.5759 15.1468C10.7206 15.412 10.9308 15.7299 11.2847 15.9489C11.702 16.2072 12.1997 16.3031 12.6831 16.2182C13.093 16.1463 13.4062 15.9292 13.6391 15.7367C13.8613 15.5529 14.1096 15.3045 14.3769 15.0371L14.377 15.0371L14.4063 15.0078C14.8325 14.5816 15.1083 14.307 15.3353 14.1157C15.5526 13.9325 15.6552 13.8878 15.7112 13.8709C15.8995 13.8141 16.1005 13.8141 16.2888 13.8709C16.3448 13.8878 16.4474 13.9325 16.6647 14.1157C16.8917 14.307 17.1675 14.5816 17.5937 15.0078L18.9441 16.3582C18.9902 15.6404 18.9983 14.7479 18.9997 13.5854Z" fill="#33363F"></path> <circle cx="16.5" cy="7.5" r="1.5" fill="#33363F"></circle> </g></svg>
                                    <span>{{file|truncate(25, True, '...')}}</span>
                                </a>

                            {% elif file.endswith(('.mp4', '.mkv')) %}
                                <a style="position: relative;" class='media-option' href="{{ url_for('uploaded_file', filename=(path ~ '/' if path else '') ~ file) }}">
                                    
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
