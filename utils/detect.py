import os
import cv2
from ultralytics import YOLO, settings

from utils.intent_command import CUBE_CLASS_NAMES


def _box_center_uv(box):
    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
    return (x1 + x2) * 0.5, (y1 + y2) * 0.5


class ObjectDetector:
    def __init__(self, model_filename="yoloe-v8s-seg.pt"):
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        model_path = os.path.join(models_dir, model_filename)
        settings.update({"weights_dir": models_dir})
        print(f"正在加载 YOLO 模型: {model_path}")
        self.model = YOLO(model_path)
        self.model.set_classes(list(CUBE_CLASS_NAMES))

    def predict(self, frame):
        return self.model.predict(frame, device="cpu", verbose=False)[0]

    def best_world_xy_for_class(
        self, frame, transformer, class_name: str, *, result=None
    ):
        result = result if result is not None else self.predict(frame)
        if len(result.boxes) == 0:
            return None
        best_uv = None
        best_conf = -1.0
        for box in result.boxes:
            name = result.names[int(box.cls[0])]
            if name != class_name:
                continue
            conf = float(box.conf[0])
            if conf <= best_conf:
                continue
            best_conf = conf
            best_uv = _box_center_uv(box)
        if best_uv is None:
            return None
        return transformer.pixel_to_world(*best_uv)

    def detect_and_draw(self, frame, transformer, *, result=None):
        result = result if result is not None else self.predict(frame)
        if len(result.boxes):
            for box in result.boxes:
                cn = result.names[int(box.cls[0])]
                u, v = _box_center_uv(box)
                conf = float(box.conf[0])
                wx, wy = transformer.pixel_to_world(u, v)
                print(
                    f"[{cn}] 置信度:{conf:.2f} | 像素:({u:.1f}, {v:.1f}) "
                    f"-> 世界坐标:({wx:.2f}, {wy:.2f})"
                )
        else:
            print("画面中未检测到目标物体。")
        cv2.imshow("Detected Space", result.plot())
        cv2.waitKey(0)
        cv2.destroyAllWindows()
