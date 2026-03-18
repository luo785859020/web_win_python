import psutil
import time
import datetime
import os
import threading
from flask import Flask, render_template, jsonify, send_from_directory, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

class SystemMonitor:
    def __init__(self):
        self.cpu_history = []
        self.memory_history = []
        self.max_history = 60
        self._last_cpu_times = None
        self._cpu_percent = 0.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._update_cpu, daemon=True)
        self._thread.start()

    def _update_cpu(self):
        while not self._stop_event.is_set():
            try:
                new_percent = psutil.cpu_percent(interval=0.5)
                with self._lock:
                    self._cpu_percent = new_percent
            except:
                pass

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1)

    def get_cpu_percent(self):
        with self._lock:
            return self._cpu_percent

    def get_memory_info(self):
        mem = psutil.virtual_memory()
        return {
            'total': self._format_bytes(mem.total),
            'available': self._format_bytes(mem.available),
            'used': self._format_bytes(mem.used),
            'percent': mem.percent
        }

    def get_disk_info(self):
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': self._format_bytes(usage.total),
                    'used': self._format_bytes(usage.used),
                    'free': self._format_bytes(usage.free),
                    'percent': usage.percent
                })
            except:
                pass
        return disks

    def get_network_info(self):
        net = psutil.net_io_counters()
        return {
            'bytes_sent': self._format_bytes(net.bytes_sent),
            'bytes_recv': self._format_bytes(net.bytes_recv),
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv
        }

    def get_processes(self):
        processes = []
        cpu_count = psutil.cpu_count() or 1

        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                info = proc.info
                cpu = proc.cpu_percent(interval=0.05) / cpu_count
                mem = proc.memory_percent()
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu': round(cpu, 1),
                    'memory': round(mem, 1),
                    'status': info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return sorted(processes, key=lambda x: x['cpu'], reverse=True)[:20]

    def get_system_info(self):
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        return {
            'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
            'platform': 'Windows',
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True)
        }

    def _format_bytes(self, bytes_value):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

monitor = SystemMonitor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

@app.route('/api/system_info')
def api_system_info():
    return jsonify(monitor.get_system_info())

@app.route('/api/cpu')
def api_cpu():
    percent = monitor.get_cpu_percent()
    return jsonify({'percent': percent})

@app.route('/api/memory')
def api_memory():
    return jsonify(monitor.get_memory_info())

@app.route('/api/disk')
def api_disk():
    return jsonify(monitor.get_disk_info())

@app.route('/api/network')
def api_network():
    return jsonify(monitor.get_network_info())

@app.route('/api/processes')
def api_processes():
    return jsonify(monitor.get_processes())

@app.route('/api/files')
def api_files():
    path = request.args.get('path', '')
    try:
        if path:
            full_path = os.path.join(BASE_DIR, path)
        else:
            full_path = BASE_DIR

        if not os.path.exists(full_path):
            return jsonify({'error': '路径不存在'}), 404

        if not os.path.isdir(full_path):
            return jsonify({'error': '不是目录'}), 400

        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            try:
                stat = os.stat(item_path)
                items.append({
                    'name': item,
                    'path': os.path.relpath(item_path, BASE_DIR),
                    'is_dir': os.path.isdir(item_path),
                    'size': stat.st_size if not os.path.isdir(item_path) else 0,
                    'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            except:
                pass

        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({'path': path, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def api_download():
    path = request.args.get('path', '')
    if not path:
        return jsonify({'error': '未指定文件路径'}), 400

    full_path = os.path.join(BASE_DIR, path)

    if '..' in path:
        return jsonify({'error': '非法路径'}), 403

    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404

    if os.path.isdir(full_path):
        return jsonify({'error': '不支持下载目录'}), 400

    return send_from_directory(BASE_DIR, path, as_attachment=True)

@app.route('/api/cmd', methods=['POST'])
def api_cmd():
    try:
        import subprocess
        data = request.get_json()
        cmd = data.get('cmd', '').strip()

        if not cmd:
            return jsonify({'error': '未指定命令'}), 400

        if any(blocked in cmd.lower() for blocked in ['rd /s /q', 'deltree', 'format', 'del /f', 'rmdir']):
            return jsonify({'error': '不允许执行此命令'}), 403

        if cmd.lower().startswith('shutdown'):
            return jsonify({'error': '请使用专用关机/重启接口'}), 403

        try:
            result = subprocess.run(
                'chcp 65001 > nul && ' + cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stdout + result.stderr
            return jsonify({
                'output': output if output else '(命令执行完成，无输出)',
                'returncode': result.returncode
            })
        except subprocess.TimeoutExpired:
            return jsonify({'error': '命令执行超时（30秒）'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shutdown', methods=['POST'])
def api_shutdown():
    try:
        data = request.get_json()
        delay = int(data.get('delay', 0))
        subprocess.run(f'shutdown -s -t {delay}', shell=True, capture_output=True)
        return jsonify({'success': True, 'message': f'将在 {delay} 秒后关机'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart', methods=['POST'])
def api_restart():
    try:
        data = request.get_json()
        delay = int(data.get('delay', 0))
        subprocess.run(f'shutdown -r -t {delay}', shell=True, capture_output=True)
        return jsonify({'success': True, 'message': f'将在 {delay} 秒后重启'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cancel_shutdown', methods=['POST'])
def api_cancel_shutdown():
    try:
        subprocess.run('shutdown -a', shell=True, capture_output=True)
        return jsonify({'success': True, 'message': '已取消定时关机/重启'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("  电脑监控系统正在启动...")
    print("  访问地址: http://localhost:5000")
    print("  局域网访问: http://<本机IP>:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)