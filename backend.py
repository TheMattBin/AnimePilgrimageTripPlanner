from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from transformers.agents import TransformersEngine, CodeAgent, ManagedAgent, ReactCodeAgent
from PIL import Image
import requests
from io import BytesIO

# 1. Load multimodal models with image support
# Router model (supports image+text classification)
router_model_id = "vikhyatk/moondream2"  # Lightweight vision-language model
router_tokenizer = AutoTokenizer.from_pretrained(router_model_id)
router_model = AutoModelForCausalLM.from_pretrained(router_model_id)
router_pipeline = pipeline("image-to-text", model=router_model, tokenizer=router_tokenizer)

# Medical agent (specialized in medical image+text)
medical_model_id = "llava-hf/llava-1.5-7b-hf"  # Replace with medical multimodal if available
med_tokenizer = AutoTokenizer.from_pretrained(medical_model_id)
med_model = AutoModelForCausalLM.from_pretrained(medical_model_id)
med_pipeline = pipeline("image-to-text", model=med_model, tokenizer=med_tokenizer)

# General QA agent (multimodal)
general_model_id = "llava-hf/llava-1.5-7b-hf"
general_tokenizer = AutoTokenizer.from_pretrained(general_model_id)
general_model = AutoModelForCausalLM.from_pretrained(general_model_id)
general_pipeline = pipeline("image-to-text", model=general_model, tokenizer=general_tokenizer)

# 2. Create engines with multimodal support
class MultimodalEngine(TransformersEngine):
    def __call__(self, inputs):
        if isinstance(inputs, Image.Image):
            return self.pipeline(inputs)
        elif isinstance(inputs, str):
            return self.pipeline(inputs)
        elif isinstance(inputs, tuple):  # (text, image)
            return self.pipeline(text=inputs[0], images=inputs[1])
        else:
            raise ValueError("Unsupported input type")

# Initialize engines
router_engine = MultimodalEngine(router_pipeline)
med_engine = MultimodalEngine(med_pipeline)
general_engine = MultimodalEngine(general_pipeline)

# 3. Wrap agents with multimodal support
med_agent = CodeAgent(tools=[], llm_engine=med_engine)
general_agent = CodeAgent(tools=[], llm_engine=general_engine)

managed_med_agent = ManagedAgent(
    agent=med_agent,
    name="medical_qa",
    description="Handles medical questions with image inputs (X-rays, skin conditions, etc.)"
)

managed_general_agent = ManagedAgent(
    agent=general_agent,
    name="general_qa",
    description="Handles general questions with image inputs"
)

# 4. Multimodal manager agent
manager_agent = ReactCodeAgent(
    tools=[],
    llm_engine=router_engine,
    managed_agents=[managed_med_agent, managed_general_agent]
)

# 5. Unified query handler
def process_query(input_data):
    """
    Handles all input types:
    - Text string: "What's in this image?"
    - Image: PIL.Image object
    - Tuple: (text, image)
    """
    return manager_agent.run(input_data)

# 6. Example usage
# Text-only query
text_response = process_query("What are symptoms of pneumonia?")

# Image-only query
image_url = "https://example.com/xray.jpg"
image = Image.open(requests.get(image_url, stream=True).raw)
image_response = process_query(image)

# Multimodal query
multimodal_response = process_query((
    "What abnormalities are visible in this lung scan?",
    Image.open(requests.get(image_url, stream=True).raw)
))
