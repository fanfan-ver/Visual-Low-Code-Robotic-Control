"""
实验任务 4：动态清理（挑战）
==============================
目标：
  请扫描桌面上的所有方块，把**除了红色以外**的所有方块，
  统统清理到“垃圾桶”区域（坐标 X=200, Y=-50）。
  红色方块必须留在原地，不能触碰。

注意：
  1. 桌面上可能出现任何颜色的方块（蓝、绿、黄等）。
  2. 每次清理完一个方块，必须让机械臂归位。

提示：你需要用到的函数：
  home()                                    - 机械臂归位
  detect_all()                              - 检测所有方块，返回字典，例如：{"red": [120, 40], "blue": [150, -20]}
  move(x, y, z)                             - 移动到指定坐标和高度
  suction_on()                              - 打开吸盘
  suction_off()                             - 关闭吸盘
  set_joint_angle_offset(j1, j2, j3, j4)    - 设置抓取姿态，固定传参 (0, 0, -30, 30)
  get_grab_z()                              - 获取抓取高度
  get_lift_z()                              - 获取抬起安全高度
  get_place_z()                             - 获取放置高度
  close()                                   - 实验结束释放资源
  实验代码运行: 在终端上输入指令: python task4_color_sort_advanced.py

请在下方 TODO 区域编写你的代码，注意必须自己写出完整的判断和抓取放置动作：
"""
from robot_api import home, detect_all, move, suction_on, suction_off, close, set_joint_angle_offset, get_grab_z, get_lift_z, get_place_z,locate

# ──── 请在下方编写代码 ────

