from functools import wraps
from hmac import compare_digest

from flask import Flask, render_template, request, send_file, Response, jsonify, redirect, session, url_for
import os
import shutil
import uuid
import queue
import threading
import time
from downloader import WebsiteDownloader, zip_directory, get_site_name
from website_downloader import (
    APP_DEBUG,
    APP_HOST,
    APP_PORT,
    APP_SECRET_KEY,
    APP_THREADED,
    DOWNLOAD_CLEANUP_DELAY_S,
    DOWNLOAD_FOLDER,
    LOGIN_PASSWORD,
    LOGIN_USERNAME,
    SESSION_CLEANUP_INTERVAL_S,
    SESSION_MAX_AGE_S,
    SSE_MESSAGE_TIMEOUT_S,
    STARTUP_CLEAN_DOWNLOADS,
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=APP_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def _safe_redirect_target(target):
    if not target or not target.startswith('/'):
        return None
    if target.startswith('//'):
        return None
    return target


def _unauthorized_response():
    if request.path == '/start-download':
        return jsonify({'error': 'Sessão expirada. Faça login novamente.'}), 401
    if request.path.startswith('/stream/') or request.path.startswith('/download-file/'):
        return Response('Unauthorized', status=401)

    next_url = request.full_path.rstrip('?') if request.query_string else request.path
    return redirect(url_for('login', next=next_url))


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('authenticated'):
            return _unauthorized_response()
        return view(*args, **kwargs)

    return wrapped_view

def cleanup_downloads_folder():
    """Remove all files and folders from downloads directory"""
    try:
        for item in os.listdir(DOWNLOAD_FOLDER):
            item_path = os.path.join(DOWNLOAD_FOLDER, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print(f"Pasta downloads limpa com sucesso")
    except Exception as e:
        print(f"Erro ao limpar pasta downloads: {e}")

if STARTUP_CLEAN_DOWNLOADS:
    cleanup_downloads_folder()

# Store for SSE messages per session
message_queues = {}
download_results = {}

def cleanup_abandoned_sessions():
    """Clean up sessions that were never downloaded after 30 minutes"""
    while True:
        time.sleep(SESSION_CLEANUP_INTERVAL_S)
        current_time = time.time()
        
        sessions_to_remove = []
        for session_id, result in list(download_results.items()):
            if result.get('status') == 'complete' and result.get('created_at'):
                age = current_time - result['created_at']
                # Remove if older than 30 minutes
                if age > SESSION_MAX_AGE_S:
                    zip_path = result.get('zip_path')
                    if zip_path and os.path.exists(zip_path):
                        try:
                            os.remove(zip_path)
                            print(f"Removido arquivo abandonado: {os.path.basename(zip_path)}")
                        except:
                            pass
                    sessions_to_remove.append(session_id)
        
        # Clean up memory
        for session_id in sessions_to_remove:
            if session_id in message_queues:
                del message_queues[session_id]
            if session_id in download_results:
                del download_results[session_id]

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_abandoned_sessions, daemon=True)
cleanup_thread.start()

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if compare_digest(username, LOGIN_USERNAME) and compare_digest(password, LOGIN_PASSWORD):
            session.clear()
            session['authenticated'] = True
            session['username'] = username
            next_url = _safe_redirect_target(request.form.get('next') or request.args.get('next'))
            return redirect(next_url or url_for('index'))

        error = 'Login ou senha incorretos.'

    return render_template('login.html', error=error)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/start-download', methods=['POST'])
@login_required
def start_download():
    """Start download process and return session ID for SSE"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Create session
    session_id = str(uuid.uuid4())
    message_queues[session_id] = queue.Queue()
    download_results[session_id] = {'status': 'processing', 'zip_path': None, 'filename': None}
    
    # Start download in background thread
    thread = threading.Thread(target=process_download, args=(session_id, url))
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})

def process_download(session_id, url):
    """Background download process"""
    q = message_queues[session_id]
    request_id = session_id
    download_dir = os.path.join(DOWNLOAD_FOLDER, request_id)
    zip_path = os.path.join(DOWNLOAD_FOLDER, f"{request_id}.zip")
    
    def log_callback(message):
        q.put(message)
    
    try:
        # Initialize downloader with log callback
        downloader = WebsiteDownloader(url, download_dir, log_callback=log_callback)
        
        # Process the site
        success = downloader.process()

        if not success:
            q.put("Falha no download")
            download_results[session_id] = {'status': 'error', 'error': 'Failed to download site'}
            return

        # Generate filename from site name
        site_name = get_site_name(url)
        zip_filename = f"{site_name}.zip"

        q.put("Criando arquivo ZIP...")
        zip_directory(download_dir, zip_path)
        
        # Cleanup raw files
        shutil.rmtree(download_dir)
        
        q.put("Download pronto!")
        download_results[session_id] = {
            'status': 'complete',
            'zip_path': zip_path,
            'filename': zip_filename,
            'created_at': time.time()
        }
        
    except Exception as e:
        q.put(f"Erro: {str(e)}")
        download_results[session_id] = {'status': 'error', 'error': str(e)}
        
        # Clean up any leftover files
        try:
            if os.path.exists(download_dir):
                shutil.rmtree(download_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except:
            pass

@app.route('/stream/<session_id>')
@login_required
def stream(session_id):
    """SSE endpoint for log streaming"""
    def generate():
        if session_id not in message_queues:
            yield f"data: Sessão não encontrada\n\n"
            return
        
        q = message_queues[session_id]
        
        while True:
            try:
                # Wait for message with timeout
                message = q.get(timeout=SSE_MESSAGE_TIMEOUT_S)
                yield f"data: {message}\n\n"
                
                # Check if download is complete
                result = download_results.get(session_id, {})
                if result.get('status') in ['complete', 'error']:
                    # Send final status
                    yield f"event: done\ndata: {result['status']}\n\n"
                    break
                    
            except queue.Empty:
                # Send keepalive
                yield f": keepalive\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download-file/<session_id>')
@login_required
def download_file(session_id):
    """Download the generated ZIP file and clean up immediately"""
    result = download_results.get(session_id)
    
    if not result or result['status'] != 'complete':
        return "File not ready", 404
    
    zip_path = result['zip_path']
    filename = result['filename']
    
    if not os.path.exists(zip_path):
        return "File not found", 404
    
    # Send file and clean up immediately after
    try:
        response = send_file(zip_path, as_attachment=True, download_name=filename)
        
        # Clean up in background thread to avoid blocking the response
        def cleanup():
            time.sleep(DOWNLOAD_CLEANUP_DELAY_S)
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    print(f"Arquivo ZIP removido: {filename}")
                if session_id in message_queues:
                    del message_queues[session_id]
                if session_id in download_results:
                    del download_results[session_id]
            except Exception as e:
                print(f"Erro ao limpar arquivo: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        return response
    except Exception as e:
        print(f"Erro ao enviar arquivo: {e}")
        return "Error sending file", 500

if __name__ == '__main__':
    # Development server
    # use_reloader=False evita cache de módulos Python
    app.run(
        host=APP_HOST,
        debug=APP_DEBUG,
        port=APP_PORT,
        threaded=APP_THREADED,
        use_reloader=False,
    )
