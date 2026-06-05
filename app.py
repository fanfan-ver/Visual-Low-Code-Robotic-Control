import sys
import io
import time
import threading
import json
import cv2
import numpy as np
import serial
from flask import Flask, render_template, request, jsonify, Response
from vlm import LocalPerceptionSystem

app = Flask(__name__, static_folder="static", template_folder="templates")

# =========================================================
# 1. 初始化本地系统
# =========================================================
print(">> [Startup] 正在启动本地 Blockly 控制中心...")
ai_system = LocalPerceptionSystem()

# 初始化机械臂串口
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    print(">> [Robot] 成功连接机械臂串口: /dev/ttyUSB0")
except Exception as e:
    print(f">> [Robot] ⚠️ 串口打开失败 (请检查接线或权限): {e}")
    ser = None

# 加载标定矩阵，计算逆变换（世界坐标 → 像素坐标）用于安全区域检查
_calib_file = "/home/test/blockly/calib_matrix_2d.json"
with open(_calib_file) as f:
    _calib = json.load(f)
_M = np.array(_calib["transform_matrix"])  # 2x3: pixel→world
# 逆矩阵: world→pixel
_A = _M[:, :2]   # 2x2 线性部分
_b = _M[:, 2]    # 2x1 平移部分
_A_inv = np.linalg.inv(_A)

# 摄像头分辨率（安全边界）
CAM_W, CAM_H = 640, 480
# 留一点边距，避免边缘误差
CAM_MARGIN = 20

def world_to_pixel(wx, wy):
    """世界坐标 → 像素坐标"""
    world = np.array([wx, wy])
    pixel = _A_inv @ (world - _b)
    return pixel[0], pixel[1]

def is_in_camera_view(wx, wy):
    """检查世界坐标是否在摄像头视野内"""
    u, v = world_to_pixel(wx, wy)
    return CAM_MARGIN <= u <= CAM_W - CAM_MARGIN and CAM_MARGIN <= v <= CAM_H - CAM_MARGIN

# =========================================================
# 2. 原子 API 定义 (本地执行版)
# =========================================================

def api_vision(target="red"):
    """
    调用本地模型进行识别
    - scene: VLM 场景图分析（带缓存）
    - 颜色: YOLO 快速定位（不跑 VLM）
    """
    if target == "scene":
        print("\n[Perception] Analyzing Scene Graph...")
        desc = ai_system.analyze_scene()
        return [0, 0]
    else:
        print(f"\n[Perception] YOLO Targeting: {target}")
        coords = ai_system.locate_target(target)
        if coords != [0, 0]:
            print(f">> Found at X:{coords[0]:.1f} Y:{coords[1]:.1f}")
        return coords

def api_move(coords, z_height, speed=50):
    """直接发送串口指令"""
    if not ser: return
    if not coords or coords == [0, 0]: return

    x, y = coords[0], coords[1]
    # 安全校验：目标点必须在摄像头视野内
    if not is_in_camera_view(x, y):
        u, v = world_to_pixel(x, y)
        msg = f"Safety: target ({x:.1f}, {y:.1f}) is outside camera view (pixel: {u:.0f}, {v:.0f})"
        print(f">> [Safety] {msg}")
        raise ValueError(msg)

    cmd = f"DescartesPoint_{x:.1f},{y:.1f},{z_height},{speed}\r\n"
    ser.write(cmd.encode('utf-8'))
    print(f"[Execution] Sent to Serial: {cmd.strip()}")
    time.sleep(2.0) # 等待机械臂完成物理运动

def api_suction(is_on):
    if not ser: return
    cmd = "Suction_1\r\n" if is_on else "Suction_0\r\n"
    ser.write(cmd.encode('utf-8'))
    print(f"[Action] Suction: {'ON' if is_on else 'OFF'}")
    time.sleep(0.5) # 等待吸盘动作完成

def api_home():
    """回到原点"""
    if not ser: return
    ser.write("Origin\r\n".encode('utf-8'))
    print("[Action] Returning to Origin...")
    time.sleep(3.0)

def api_pick_ready():
    """抓取前姿态调整：JointAngleOffset 一步到位，避免两步运动漂移"""
    if not ser: return
    ser.write("JointAngleOffset_0,0,-30,30\r\n".encode('utf-8'))
    print("[Action] Pick ready: JointAngleOffset applied.")
    time.sleep(0.8)

def api_snapshot():
    """拍照保存当前画面"""
    frame = ai_system.get_frame()
    if frame is not None:
        import os, datetime
        save_dir = "/home/test/blockly/snapshots"
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(save_dir, f"snap_{ts}.jpg")
        cv2.imwrite(path, frame)
        print(f"[Snapshot] Saved: {path}")
    else:
        print("[Snapshot] Camera capture failed.")

# =========================================================
# 3. 路由逻辑
# =========================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_scene')
def analyze_scene():
    """独立的场景图接口，前端每次 Run 时自动调用"""
    try:
        scene_graph = ai_system.analyze_scene()
        return jsonify({"status": "success", "scene_graph": scene_graph})
    except Exception as e:
        return jsonify({"status": "error", "scene_graph": str(e)}), 500

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            frame = ai_system.get_frame()
            if frame is not None:
                h, w = frame.shape[:2]
                cv2.circle(frame, (w//2, h//2), 5, (0, 255, 0), -1)
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.05)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/safety_check', methods=['POST'])
def safety_check():
    """预检：提取代码中所有坐标，检查是否在摄像头视野内"""
    try:
        data = request.json
        python_code = data.get('code', '')
        # 匹配 api_move([x, y], z) 中的坐标
        import re
        pattern = r'api_move\(\s*\[([^,]+),\s*([^\]]+)\]'
        matches = re.findall(pattern, python_code)
        violations = []
        for x_str, y_str in matches:
            try:
                x, y = float(x_str.strip()), float(y_str.strip())
                if not is_in_camera_view(x, y):
                    u, v = world_to_pixel(x, y)
                    violations.append(
                        f"Target ({x:.1f}, {y:.1f}) is outside camera view (pixel: {u:.0f}, {v:.0f})"
                    )
            except ValueError:
                pass  # 变量引用，跳过静态检查
        if violations:
            return jsonify({"safe": False, "violations": violations})
        return jsonify({"safe": True, "violations": []})
    except Exception as e:
        return jsonify({"safe": False, "violations": [str(e)]}), 500

@app.route('/execute_code', methods=['POST'])
def execute_code():
    try:
        data = request.json
        python_code = data.get('code', '')
        print(f"\n{'='*40}\n[DEBUG] 生成的Python代码:\n{python_code}\n{'='*40}")
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()

        context = {
            "__builtins__": {},
            "range": range,
            "len": len,
            "int": int,
            "float": float,
            "str": str,
            "True": True,
            "False": False,
            "None": None,
            "api_vision": api_vision,
            "api_move": api_move,
            "api_suction": api_suction,
            "api_home": api_home,
            "api_pick_ready": api_pick_ready,
            "api_snapshot": api_snapshot,
            "print": print,
            "time": time,
        }

        exec(python_code, context)
        sys.stdout = old_stdout
        output = redirected_output.getvalue()
        print(f"[DEBUG] 执行输出:\n{output}")
        return jsonify({"status": "success", "message": output})
    except Exception as e:
        if 'old_stdout' in locals(): sys.stdout = old_stdout
        print(f"[DEBUG] 执行异常: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6006, debug=False)