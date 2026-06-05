"""
机械臂 Python 对照组 API
========================
高层封装，志愿者只需调用: pick, place, pick_and_place, home, locate, wait, close
坐标管道复用 version1 的 YOLO 中心点 + 标定矩阵（已验证准确）
"""
import sys
import os
import time
import threading
import serial
import cv2
import numpy as np

BLOCKLY_ROOT = "/home/test/blockly"
VERSION1_ROOT = "/home/test/version1"
if VERSION1_ROOT not in sys.path:
    sys.path.insert(0, VERSION1_ROOT)

from utils.detect import ObjectDetector
from utils.transform import CoordinateTransformer

# ─── 运动参数（对齐 version1 调校值）─────────────────────────
Z_GRAB = 180.0      # 下降抓取高度
Z_LIFT = 223.0      # 抬起安全高度
Z_PLACE = 180.0     # 放置高度
SPEED = 50.0        # 运动速度
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 115200
CAMERA_INDEX = 1
CAMERA_W, CAMERA_H = 640, 480
CALIB_FILE = os.path.join(BLOCKLY_ROOT, "calib_matrix_2d.json")


class _RobotSystem:
    """内部系统类，管理硬件连接和感知组件"""

    def __init__(self):
        print("\n" + "=" * 50)
        print(">> [初始化] 正在启动实验系统...")

        # 1. YOLO 检测器 + 坐标转换器（复用 version1）
        self.detector = ObjectDetector(model_filename="yoloe-v8s-seg.pt")
        self.transformer = CoordinateTransformer(calib_file=CALIB_FILE)

        # 2. 摄像头 + 后台采集线程
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_H)
        self._frame = None
        self._frame_lock = threading.Lock()
        self._frame_count = 0
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        time.sleep(1.0)

        # 3. 串口长连接
        try:
            self.ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            time.sleep(0.5)
            print(f">> [串口] 已连接: {SERIAL_PORT}")
        except Exception as e:
            self.ser = None
            print(f">> [串口] 连接失败: {e}")

        print(">> [系统] 实验环境就绪")
        print("=" * 50 + "\n")

    def _capture_loop(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                with self._frame_lock:
                    self._frame = frame.copy()
                    self._frame_count = getattr(self, '_frame_count', 0) + 1
            cv2.waitKey(10)

    def get_frame(self):
        with self._frame_lock:
            return self._frame.copy() if self._frame is not None else None

    def get_fresh_frame(self):
        """等待后台线程刷新足够多帧，确保拿到实时画面"""
        with self._frame_lock:
            self._frame_count = 0
        deadline = time.time() + 5.0
        while time.time() < deadline:
            time.sleep(0.05)
            with self._frame_lock:
                if self._frame_count >= 30 and self._frame is not None:
                    return self._frame.copy()
        return self.get_frame()

    def send_cmd(self, cmd):
        if not self.ser:
            print(f">> [警告] 串口未连接，跳过: {cmd}")
            return
        line = cmd if cmd.endswith("\r\n") else cmd + "\r\n"
        self.ser.write(line.encode("utf-8"))
        self.ser.flush()

    def locate_color(self, color):
        """用 YOLO 中心点定位 + 标定矩阵转世界坐标"""
        time.sleep(2.0)
        frame = self.get_fresh_frame()
        if frame is None:
            print(">> [感知] 摄像头画面为空")
            return None

        class_name = f"{color.capitalize()} Cube"
        world_xy = self.detector.best_world_xy_for_class(
            frame, self.transformer, class_name
        )
        if world_xy is None:
            print(f">> [感知] 未检测到 {class_name}")
            return None

        coords = [float(world_xy[0]), float(world_xy[1])]
        print(f">> [感知] {class_name} -> 世界坐标 ({coords[0]:.1f}, {coords[1]:.1f})")
        return coords

    def detect_all(self):
        """检测视野内所有方块，返回 {颜色: [x,y]} 字典"""
        time.sleep(0.5)
        frame = self.get_frame()
        if frame is None:
            return {}

        result = self.detector.predict(frame)
        found = {}
        if len(result.boxes) > 0:
            for box in result.boxes:
                name = result.names[int(box.cls[0])]
                xy = self.detector.best_world_xy_for_class(
                    frame, self.transformer, name, result=result
                )
                if xy:
                    color_key = name.replace(" Cube", "").lower()
                    found[color_key] = [float(xy[0]), float(xy[1])]
        return found

    def move_to(self, x, y, z):
        cmd = f"DescartesPoint_{x:.1f},{y:.1f},{z},{SPEED}"
        self.send_cmd(cmd)
        print(f">> [运动] X:{x:.1f} Y:{y:.1f} Z:{z}")
        time.sleep(2.0)

    def suction_on(self):
        self.send_cmd("Suction_1")
        print(">> [吸盘] 开启")
        time.sleep(0.8)

    def suction_off(self):
        self.send_cmd("Suction_0")
        print(">> [吸盘] 关闭")
        time.sleep(0.8)

    def go_home(self):
        """回到原点"""
        self.send_cmd("Origin")
        print(">> [归位] Origin...")
        time.sleep(3.0)
        print(">> [归位] 完成")

    def do_pick(self, coords):
        """抓取序列：对齐 RobotArmVlm 的 _pick_sequence"""
        x, y = coords[0], coords[1]
        self.send_cmd("JointAngleOffset_0,0,-30,30")
        time.sleep(0.8)
        self.move_to(x, y, Z_GRAB)
        self.suction_on()
        self.move_to(x, y, Z_LIFT)

    def do_place(self, x, y, z=Z_PLACE):
        """放置序列"""
        self.move_to(x, y, Z_LIFT)
        self.move_to(x, y, z)
        self.suction_off()
        self.move_to(x, y, Z_LIFT)

    def shutdown(self):
        print("\n>> [系统] 正在释放资源...")
        if self.ser:
            self.ser.close()
        if self.cap:
            self.cap.release()
        print(">> [系统] 已安全退出")


# ─── 全局实例（导入时自动初始化）─────────────────────────────
_sys = _RobotSystem()


# ═══════════════════════════════════════════════════════════
# 志愿者可用的公开 API
# ═══════════════════════════════════════════════════════════

def home():
    """机械臂归位（每次实验开始前必须调用）"""
    _sys.go_home()


def locate(color):
    """
    定位指定颜色的方块
    参数: color - 颜色名称，如 "red", "blue", "green", "yellow"
    返回: [x, y] 坐标列表，未找到返回 None
    """
    return _sys.locate_color(color)


def set_joint_angle_offset(j1, j2, j3, j4):
    """底层API: 设置关节角度偏移"""
    cmd = f"JointAngleOffset_{j1},{j2},{j3},{j4}"
    _sys.send_cmd(cmd)
    time.sleep(0.8)


def get_grab_z():
    """获取抓取高度 Z 轴常量"""
    return Z_GRAB


def get_lift_z():
    """获取抬起安全高度 Z 轴常量"""
    return Z_LIFT


def get_place_z():
    """获取放置高度 Z 轴常量"""
    return Z_PLACE


def detect_all():
    """
    检测视野内所有方块
    返回: 字典，如 {"red": [200, 30], "blue": [180, -40]}
    """
    return _sys.detect_all()


def pick(color):
    """
    识别并抓取指定颜色的方块
    参数: color - 颜色名称，如 "red"
    返回: True 成功 / False 失败
    """
    coords = _sys.locate_color(color)
    if coords is None:
        print(f">> [抓取] 失败：未找到 {color} 方块")
        return False
    _sys.do_pick(coords)
    print(f">> [抓取] 已抓取 {color} 方块")
    return True


def place(x, y, z=Z_PLACE):
    """
    将手中的方块放置到指定坐标
    参数: x, y - 目标世界坐标; z - 放置高度(可选)
    """
    _sys.do_place(x, y, z)
    print(f">> [放置] 已放置到 ({x:.1f}, {y:.1f})")


def pick_and_place(color, target_x, target_y, place_z=Z_PLACE):
    """
    一键完成：识别方块 → 抓取 → 搬运到目标位置
    参数: color - 颜色; target_x, target_y - 目标坐标; place_z - 放置高度(可选)
    返回: True 成功 / False 失败
    """
    if not pick(color):
        return False
    place(target_x, target_y, place_z)
    return True


def wait(seconds):
    """等待指定秒数"""
    time.sleep(seconds)


def move(x, y, z):
    """
    移动机械臂到指定坐标和高度
    参数: x, y - 世界坐标; z - 高度
    """
    _sys.move_to(x, y, z)


def suction_on():
    """打开吸盘"""
    _sys.suction_on()


def suction_off():
    """关闭吸盘"""
    _sys.suction_off()


def close():
    """释放所有资源（实验结束时调用）"""
    _sys.shutdown()
