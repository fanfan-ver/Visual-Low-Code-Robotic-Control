"""
实验任务 1：基础操作（入门）
============================
目标：
  1. 让机械臂归位
  2. 移动机械臂到坐标 (200, 30)，高度 Z=200
  3. 打开吸盘
  4. 等待 2 秒
  5. 关闭吸盘
  6. 让机械臂归位

提示：你需要用到的函数：
  home()               - 机械臂归位
  move(x, y, z)        - 移动到指定坐标和高度
  suction_on()         - 打开吸盘
  suction_off()        - 关闭吸盘
  wait(秒数)            - 等待指定秒数
  close()              - 实验结束释放资源
实验代码运行：在终端输入指令：python task1_single_move.py

请在下方 TODO 区域编写你的代码：
"""
from robot_api import home, move, suction_on, suction_off, wait, close,locate,set_joint_angle_offset,get_lift_z

# ──── 请在下方编写代码 ────


