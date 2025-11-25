# webUI.py
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import pandas as pd
from config import Config
from task_manager import task_manager
import time

app = Flask(__name__)
app.config.from_object(Config)

# 初始化JWT
jwt = JWTManager(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 设置任务管理器的socketio实例
task_manager.set_socketio(socketio)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def jwt_required_cookie():
    """自定义装饰器，从cookie中获取token"""

    def wrapper(fn):
        from functools import wraps

        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                # 首先尝试从cookie获取token
                token = request.cookies.get('access_token')
                if token:
                    # 手动设置Authorization头
                    request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'

                verify_jwt_in_request()
                return fn(*args, **kwargs)
            except NoAuthorizationError:
                return jsonify({'status': 'error', 'message': '未授权访问'}), 401

        return decorator

    return wrapper


# WebSocket连接认证
@socketio.on('connect')
def handle_connect():
    # 检查认证
    token = request.cookies.get('access_token')
    if not token:
        return False

    try:
        from flask_jwt_extended import decode_token
        decode_token(token)
        print("WebSocket连接已建立")

        # 发送历史日志
        history_logs = task_manager.get_logs(50)
        emit('log_history', history_logs)
    except:
        return False


@socketio.on('disconnect')
def handle_disconnect():
    print('WebSocket连接已断开')


# 登录页面
@app.route('/')
def index():
    return redirect(url_for('login_page'))


# webUI.py 中的登录路由
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in app.config['USERS'] and app.config['USERS'][username] == password:
            access_token = create_access_token(identity=username)
            response = make_response(redirect(url_for('dashboard_page')))
            response.set_cookie('access_token', access_token, httponly=True, secure=False)
            return response
        else:
            # 如果是AJAX请求，返回JSON错误
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                    request.headers.get('Content-Type') == 'application/json':
                return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
            else:
                # 传统表单提交，返回带错误信息的页面
                return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html')


# 登出
@app.route('/logout')
def logout_page():
    response = make_response(redirect(url_for('login_page')))
    response.set_cookie('access_token', '', expires=0)
    return response


# 仪表板页面
@app.route('/dashboard')
def dashboard_page():
    # 检查是否已登录
    token = request.cookies.get('access_token')
    if not token:
        return redirect(url_for('login_page'))

    try:
        # 验证token
        from flask_jwt_extended import decode_token
        decode_token(token)
        return render_template('dashboard.html')
    except:
        return redirect(url_for('login_page'))


# API路由
@app.route('/api/start_task', methods=['POST'])
@jwt_required_cookie()
def api_start_task():
    if task_manager.is_running:
        return jsonify({'status': 'error', 'message': '任务已在运行中'})

    task_manager.run_main()
    return jsonify({'status': 'success', 'message': '任务已启动'})


@app.route('/api/stop_task', methods=['POST'])
@jwt_required_cookie()
def api_stop_task():
    if not task_manager.is_running:
        return jsonify({'status': 'error', 'message': '没有正在运行的任务'})

    task_manager.stop_main()
    return jsonify({'status': 'success', 'message': '任务已停止'})


@app.route('/api/task_status', methods=['GET'])
@jwt_required_cookie()
def api_task_status():
    status = task_manager.get_status()
    return jsonify(status)


@app.route('/api/upload', methods=['POST'])
@jwt_required_cookie()
def api_upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有选择文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # 备份原文件
        if os.path.exists(app.config['EXCEL_FILE']):
            backup_name = f"backup_{int(time.time())}_{app.config['EXCEL_FILE']}"
            os.rename(app.config['EXCEL_FILE'], os.path.join(app.config['UPLOAD_FOLDER'], backup_name))

        # 保存新文件
        file.save(app.config['EXCEL_FILE'])

        return jsonify({'status': 'success', 'message': '文件上传成功'})

    return jsonify({'status': 'error', 'message': '文件类型不支持'})


@app.route('/api/download', methods=['GET'])
def api_download_file():
    # 检查cookie中的token
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'status': 'error', 'message': '未授权访问'}), 401

    try:
        from flask_jwt_extended import decode_token
        decode_token(token)
    except:
        return jsonify({'status': 'error', 'message': 'token无效'}), 401

    if not os.path.exists(app.config['EXCEL_FILE']):
        return jsonify({'status': 'error', 'message': '文件不存在'}), 404

    return send_file(
        app.config['EXCEL_FILE'],
        as_attachment=True,
        download_name='info-auto.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/api/file_info', methods=['GET'])
@jwt_required_cookie()
def api_file_info():
    if not os.path.exists(app.config['EXCEL_FILE']):
        return jsonify({'status': 'error', 'message': '文件不存在'})
    return jsonify({'status': 'success', 'message': '文件存在'})


# 修改 webUI.py 的最后一行
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
