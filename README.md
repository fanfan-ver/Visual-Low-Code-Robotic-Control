# Visual-Low-Code-Robotic-Control
Official repository for the paper: **"A Visual Low-Code Robotic Control Framework with Hybrid Semantic-Geometric Perception for Non-Expert Operators"**.

## 📄 Documentation
- **[Read the Paper (PDF)](./paper.pdf)**  
- **[System Highlights & Abstract](https://github.com/fanfan-ver/Visual-Low-Code-Robotic-Control#introduction)**

## 🛠️ Key Features
- **Visual Low-Code Interface**: Built on Blockly for intuitive task orchestration.
- **Hybrid Perception**: Dual-track engine integrating Florence-2 (VLM) and YOLOv8.
- **Proactive Safety**: Pre-execution validation to prevent workspace collisions.

## 📂 Repository Structure
- `app.py`: Main Flask server and backend logic.
- `vlm.py`: Vision-Language Model integration logic.
- `/utils`: Coordinate transformation and object detection utilities.
- `/robot_python_experiment`: Scripts and task templates used in the user study.

## 📦 Model Weights
Due to size limits, pre-trained weights are hosted in the **[Releases](../../releases)** section:
1. **YOLOv8 Segmentation**: Download `yoloe-v8s-seg.pt`.
2. **VLM (Florence-2)**: Please refer to the paper for downloading instructions.

## 🚀 Quick Start
1. Clone the repo: `git clone https://github.com/fanfan-ver/Visual-Low-Code-Robotic-Control.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python app.py`
