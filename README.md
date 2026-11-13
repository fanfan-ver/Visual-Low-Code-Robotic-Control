# Visual Low-Code Robotic Control

An anonymized research artifact for a web-based visual low-code robotic control framework integrating hybrid semantic-geometric perception and pre-execution safety validation.

## 🛠️ Key Features

- **Visual Low-Code Interface:** Built on Blockly for intuitive task orchestration.
- **Hybrid Perception:** Integrates Florence-2 (VLM) for semantic understanding and YOLOv8 for object detection and localization.
- **Proactive Safety:** Performs pre-execution validation to check target coordinates against workspace constraints.

## 📂 Repository Structure

- `app.py`: Main Flask server and backend logic.
- `vlm.py`: Vision-language model integration.
- `/utils`: Coordinate transformation and object detection utilities.
- `/robot_python_experiment`: Scripts and task templates used in the user study.

## 📦 Model Weights

Due to file size limitations, pre-trained model weights are distributed separately from the source code.

1. **YOLOv8 Segmentation:** The checkpoint file is `yoloe-v8s-seg.pt`. It should be placed in the `/models` directory before execution.
2. **Florence-2:** Please follow the model acquisition instructions and configuration requirements described in the paper.

<!-- Add the exact anonymized artifact release URL here only after verifying that it is accessible to reviewers. -->

## 🚀 Quick Start

1. Clone or download this repository.
2. Install the required dependencies:

   `pip install -r requirements.txt`

3. Configure the required model weights and settings.
4. Run the application:

   `python app.py`

## 🔬 Reproducibility

This repository provides the framework implementation and relevant experimental scripts. Individual-level user-study data are not included due to participant privacy considerations. The experimental setup, evaluation metrics, and aggregated results are reported in the accompanying paper.
