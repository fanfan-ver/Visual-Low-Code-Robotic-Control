import torch
import cv2
import os
import sys
import time
import threading
import numpy as np
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM, AutoConfig

# 关联隔壁的 YOLO 文件夹
sys.path.append("/home/test/version1")
try:
    from utils.detect import ObjectDetector
    from utils.transform import CoordinateTransformer
except ImportError:
    print(" 无法找到 version1 文件夹")

class LocalPerceptionSystem:
    def __init__(self):
        print("\n" + "="*60)
        model_path = "/home/test/blockly/models_vlm/AI-ModelScope/Florence-2-base"
        self.device = "cpu"

        print(f">> [大脑] 正在以纯 CPU 模式加载 VLM (已解除硬件限制)...")

        # 1. 修正配置
        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        config.attn_implementation = "sdpa"
        if hasattr(config, "text_config"):
            config.text_config.forced_bos_token_id = None
            config.text_config.forced_eos_token_id = None

        # 2. 加载模型
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            config=config,
            trust_remote_code=True,
            attn_implementation="sdpa",
            torch_dtype=torch.float32
        ).to(self.device).eval()

        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)

        # 3. 加载学长组件
        self.yolo_detector = ObjectDetector(model_filename="yoloe-v8s-seg.pt")
        self.transformer = CoordinateTransformer(calib_file="/home/test/blockly/calib_matrix_2d.json")

        # 4. 摄像头 + 共享帧缓冲区（后台线程采集，避免多线程抢占）
        self.cap = cv2.VideoCapture(1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._frame = None
        self._frame_lock = threading.Lock()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        # 5. 场景图缓存
        self._scene_cache = None
        self._frame_count = 0

        print(">> [System] ✅ 本地化 AI 系统初始化完成！")
        print("="*60 + "\n")

    def _capture_loop(self):
        """后台线程持续采集摄像头画面，存入共享缓冲区"""
        while True:
            ret, frame = self.cap.read()
            if ret:
                with self._frame_lock:
                    self._frame = frame.copy()
                    self._frame_count = getattr(self, '_frame_count', 0) + 1
            cv2.waitKey(10)

    def get_frame(self):
        """获取最新一帧，所有需要摄像头画面的地方都用这个"""
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

    def analyze_scene(self):
        """VLM 场景图分析：用 OD prompt 识别所有物体及位置关系，结果缓存"""
        frame = self.get_frame()
        if frame is None:
            return "Camera Error"

        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # 用 <OD> prompt 让 Florence-2 做目标检测，返回物体+边界框
        inputs = self.processor(text="<OD>", images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=512,
                num_beams=1
            )
        raw = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        parsed = self.processor.post_process_generation(raw, task="<OD>", image_size=image.size)

        # 同时用 YOLO 检测物体及其像素位置（YOLO 对方块更准）
        yolo_result = self.yolo_detector.predict(frame)

        scene_lines = []
        relations = []

        yolo_objects = {}
        if len(yolo_result.boxes) > 0:
            for box in yolo_result.boxes:
                name = yolo_result.names[int(box.cls[0])]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                yolo_objects[name] = {"cx": cx, "cy": cy, "x1": x1, "y1": y1, "x2": x2, "y2": y2}

        # 为每个物体标注位置
        name_list = list(yolo_objects.keys())
        for i, name in enumerate(name_list):
            obj = yolo_objects[name]
            h_pos = "left" if obj["cx"] < 213 else ("right" if obj["cx"] > 427 else "center")
            v_pos = "top" if obj["cy"] < 160 else ("bottom" if obj["cy"] > 320 else "middle")
            scene_lines.append(f"- {name} ({h_pos}, {v_pos})")

        # 计算物体间空间关系
        for i in range(len(name_list)):
            for j in range(i + 1, len(name_list)):
                a = yolo_objects[name_list[i]]
                b = yolo_objects[name_list[j]]
                if a["cx"] < b["cx"] - 50:
                    relations.append(f"{name_list[i]} is left of {name_list[j]}")
                elif a["cx"] > b["cx"] + 50:
                    relations.append(f"{name_list[i]} is right of {name_list[j]}")
                h_overlap = min(a["x2"], b["x2"]) - max(a["x1"], b["x1"])
                if h_overlap > 30:
                    if a["cy"] < b["cy"] - 20:
                        relations.append(f"{name_list[i]} is stacked on {name_list[j]}")
                    elif b["cy"] < a["cy"] - 20:
                        relations.append(f"{name_list[j]} is stacked on {name_list[i]}")

        # 组装场景图
        header = "Scene Graph:" if scene_lines else "No objects detected."
        scene_graph = header
        for line in scene_lines:
            scene_graph += "\n" + line
        if relations:
            scene_graph += "\nRelations: " + ", ".join(relations)

        self._scene_cache = scene_graph
        print(f"[场景理解]\n{scene_graph}")
        return scene_graph

    def locate_target(self, target_color="red"):
        """YOLO 快速定位目标方块，不跑 VLM"""
        time.sleep(2.0)
        frame = self.get_fresh_frame()
        if frame is None:
            return [0, 0]
        class_name = f"{target_color.capitalize()} Cube"
        world_xy = self.yolo_detector.best_world_xy_for_class(frame, self.transformer, class_name)
        if world_xy:
            return list(world_xy)
        return [0, 0]
