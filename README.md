Visual Low-Code Robotic Control

An anonymized research artifact for a web-based visual low-code robotic control framework integrating hybrid semantic-geometric perception and pre-execution safety validation.

🛠️ Key Features

Visual Low-Code Interface: Built on Blockly for intuitive task orchestration.

Hybrid Perception: Integrates Florence-2 (VLM) for semantic understanding and YOLOv8 for object detection and localization.

Proactive Safety: Performs pre-execution validation to check target coordinates against workspace constraints.

📂 Repository Structure

app.py: Main Flask server and backend logic.

vlm.py: Vision-language model integration.

/utils: Coordinate transformation and object detection utilities.

/robot_python_experiment: Scripts and task templates used in the user study.

📦 Model Weights

Due to file size limitations, pre-trained model weights are distributed separately from the source code.

YOLOv8 Segmentation: The checkpoint file is yoloe-v8s-seg.pt. It should be placed in the /models directory before execution.

Florence-2: Please follow the model acquisition instructions and configuration requirements described in the paper.

<!-- Add the exact anonymized artifact release URL here only after verifying that it is accessible to reviewers. -->

🚀 Quick Start

Clone or download this repository.

Install the required dependencies:

pip install -r requirements.txt

Configure the required model weights and settings.

Run the application:

python app.py
