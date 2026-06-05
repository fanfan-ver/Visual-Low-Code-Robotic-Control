import json
import os
import numpy as np

from utils.paths import bundled_data_dir


class CoordinateTransformer:
    def __init__(self, calib_file="calib_matrix_2d.json"):
        if not os.path.isabs(calib_file):
            calib_file = os.path.join(bundled_data_dir(), "calibration", calib_file)

        if not os.path.exists(calib_file):
            raise FileNotFoundError(f"未找到标定文件: {calib_file}")

        with open(calib_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.transform_matrix = np.array(data["transform_matrix"], dtype=float)

    def pixel_to_world(self, u, v):
        pixel_homo = np.array([u, v, 1.0])
        world_xy = pixel_homo @ self.transform_matrix.T
        return world_xy[0], world_xy[1]
