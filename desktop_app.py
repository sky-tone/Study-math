"""
小升初数学 · 桌面版应用
========================
将 Streamlit Web 应用封装为独立桌面窗口，双击即可运行。

启动方式：
    python desktop_app.py
    或双击 run_desktop.bat

工作原理：
    1. 在后台启动 Streamlit 服务器
    2. 用 Edge/Chrome 的 App 模式打开（无地址栏/标签页，看起来像原生应用）
    3. 关闭浏览器窗口后自动退出

无需额外安装任何依赖（Edge 已预装在 Windows 10/11 上）。
"""

import sys
import os
import subprocess
import time
import socket
import atexit
import urllib.request
import webbrowser

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
APP_TITLE = "小升初数学 · 教学与测验系统"
SERVER_TIMEOUT = 30  # 等待服务器启动的最大秒数

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY = os.path.join(BASE_DIR, "app.py")

# ---------------------------------------------------------------------------
# 服务器管理
# ---------------------------------------------------------------------------
_server_process = None


def _find_free_port():
    """找到一个可用的本地端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _start_server(port):
    """在后台启动 Streamlit 服务器"""
    global _server_process

    kwargs = dict(
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Windows: 隐藏控制台窗口
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STUDY_MATH_DESKTOP"] = "1"  # 让 app.py 知道在桌面模式
    kwargs["env"] = env

    _server_process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", APP_PY,
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--global.developmentMode", "false",
        ],
        **kwargs,
    )


def _stop_server():
    """停止 Streamlit 服务器"""
    global _server_process
    if _server_process and _server_process.poll() is None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None


def _wait_for_server(port, timeout=SERVER_TIMEOUT):
    """等待服务器就绪（先检查健康端点，再确认主页可访问）"""
    health_url = f"http://localhost:{port}/_stcore/health"
    main_url = f"http://localhost:{port}/"
    deadline = time.time() + timeout

    # 阶段1：等待健康端点
    while time.time() < deadline:
        if _server_process and _server_process.poll() is not None:
            return False
        try:
            resp = urllib.request.urlopen(health_url, timeout=2)
            if resp.status == 200:
                break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        return False

    # 阶段2：等待主页面可访问
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(main_url, timeout=3)
            if resp.status == 200:
                time.sleep(1)  # 额外等待确保完全加载
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# 浏览器查找
# ---------------------------------------------------------------------------
def _find_browser_exe():
    """查找 Edge 或 Chrome 可执行文件（支持 --app 模式）"""
    candidates = [
        # Microsoft Edge（Windows 预装）
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
def main():
    # 检查 app.py 存在
    if not os.path.exists(APP_PY):
        print(f"[ERROR] 找不到 {APP_PY}")
        input("按回车键退出...")
        return

    port = _find_free_port()
    url = f"http://localhost:{port}"
    atexit.register(_stop_server)

    # 1) 启动 Streamlit 服务器
    print(f"[INFO] 正在启动服务器 (端口 {port}) ...")
    _start_server(port)

    if not _wait_for_server(port):
        print("[ERROR] 服务器启动失败。")
        print("        请确认已安装 streamlit: pip install streamlit")
        _stop_server()
        input("按回车键退出...")
        return

    print("[OK] 服务器已就绪！")

    # 2) 用浏览器 App 模式打开
    browser_exe = _find_browser_exe()
    browser_proc = None

    if browser_exe:
        browser_name = os.path.basename(browser_exe).replace(".exe", "")
        print(f"[INFO] 正在打开桌面窗口 ({browser_name}) ...")

        # 使用独立 user-data-dir 避免与已运行的浏览器冲突
        # 已运行的 Edge/Chrome 会拦截 --app 参数导致 URL 丢失
        user_data = os.path.join(BASE_DIR, ".browser_data")
        os.makedirs(user_data, exist_ok=True)

        browser_proc = subprocess.Popen([
            browser_exe,
            f"--app={url}",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-size=1280,860",
        ])
    else:
        print(f"[INFO] 在默认浏览器中打开: {url}")
        webbrowser.open(url)

    print(f"[OK] {APP_TITLE} 已启动！")
    print()

    # 3) 等待浏览器窗口关闭
    if browser_proc:
        print("[INFO] 关闭应用窗口后将自动退出。")
        try:
            browser_proc.wait()
        except KeyboardInterrupt:
            pass
    else:
        print("[INFO] 按 Ctrl+C 可退出。")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # 4) 清理
    _stop_server()
    print("[OK] 应用已关闭。")


if __name__ == "__main__":
    main()
