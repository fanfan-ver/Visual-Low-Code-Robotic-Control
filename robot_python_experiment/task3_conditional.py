"""
实验任务 3：多方块搬运（进阶）
==============================
目标：
  1. 把红色方块搬到坐标 (200, 30)
  2. 把蓝色方块搬到坐标 (170, 30)

注意：每次搬完一个方块后，需要让机械臂归位，
      避免机械臂挡住摄像头导致下一次识别失败。

提示：你需要用到的函数：
  home()                                    - 机械臂归位
  move(x, y, z)                             - 移动到指定坐标和高度
  suction_on()                              - 打开吸盘
  suction_off()                             - 关闭吸盘
  set_joint_angle_offset(j1, j2, j3, j4)    - 设置抓取姿态，固定传参 (0, 0, -30, 30)
  get_grab_z()                              - 获取抓取高度
  get_lift_z()                              - 获取抬起安全高度
  get_place_z()                             - 获取放置高度
  close()                                   - 实验结束释放资源
实验代码运行：在终端输入指令: python task3_conditional.py
请在下方 TODO 区域编写你的代码：
"""
from robot_api import home, locate, move, suction_on, suction_off, wait, close, set_joint_angle_offset, get_grab_z, get_lift_z, get_place_z

# ──── 请在下方编写代码 ────
