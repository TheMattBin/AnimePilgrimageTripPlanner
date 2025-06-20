from PIL import Image

import torch
from smolagents import MultiStepAgent, CodeAgent, TransformersModel

# === Configuration ===
MODELS = {
    "router": "microsoft/Phi-3-mini-4k-instruct",
    # "medical": "google/medgemma-4b-it",
    "medical": "prithivMLmods/Radiology-Infer-Mini",
    "general": "Qwen/Qwen1.5-0.5B"
}

# === Model Initialization ===
def create_smol_model(model_id):
    return TransformersModel(
        model_id=model_id,
        device_map="auto",
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )

# === Agent Setup ===
# Medical Agent (MedGemma)
medical_agent = CodeAgent(
    tools=[],
    model=create_smol_model(MODELS["medical"]),
    name="medical_qa",
    description="Handles medical questions with image analysis"
)

# General QA Agent
general_agent = CodeAgent(
    tools=[],
    model=create_smol_model(MODELS["general"]),
    name="general_qa",
    description="Handles general knowledge questions"
)

# === Manager/Router Agent ===
class RouterAgent(MultiStepAgent):
    def initialize_system_prompt(self):
        return """
        You are a routing agent. Classify queries into:
        - Medical: Symptoms, conditions, medications, health advice
        - General: Non-medical questions, facts, explanations

        Respond ONLY with:
        - "medical_qa" for medical queries
        - "general_qa" for general queries
        """

manager_agent = RouterAgent(
    tools=[],
    model=create_smol_model(MODELS["router"]),
    managed_agents=[medical_agent, general_agent],
    name="router",
    description="Routes queries to appropriate domain agents"
)

# === Unified Query Processor ===
def process_query(input_data):
    """
    Handles:
    - Text: "What are symptoms of pneumonia?"
    - Image: PIL.Image object
    - Multimodal: (text, image)
    """
    return manager_agent.run(task=str(input_data))

# === Example Usage ===
if __name__ == "__main__":
    # Text-only medical query
    print(process_query("What are symptoms of diabetes?"))

    # Medical image analysis
    from PIL import Image
    xray_image = Image.open("chest_xray.png")
    print(process_query(("Analyze this lung scan", xray_image)))

    # General knowledge query
    print(process_query("Explain quantum computing in simple terms"))
