from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from transformers.agents import TransformersEngine, CodeAgent, ManagedAgent, ReactCodeAgent

# 1. Load your models as pipelines
# Replace with your preferred models or local paths
router_model_id = "Qwen/Qwen1.5-0.5B"
medical_model_id = "medicalai/Qwen-Med"
general_model_id = "Qwen/Qwen1.5-7B"

# Router agent (for routing/classification)
router_tokenizer = AutoTokenizer.from_pretrained(router_model_id)
router_model = AutoModelForCausalLM.from_pretrained(router_model_id)
router_pipeline = pipeline("text-generation", model=router_model, tokenizer=router_tokenizer)
router_engine = TransformersEngine(router_pipeline)

# Medical agent
med_tokenizer = AutoTokenizer.from_pretrained(medical_model_id)
med_model = AutoModelForCausalLM.from_pretrained(medical_model_id)
med_pipeline = pipeline("text-generation", model=med_model, tokenizer=med_tokenizer)
med_engine = TransformersEngine(med_pipeline)
med_agent = CodeAgent(tools=[], llm_engine=med_engine)

# General QA agent
qa_tokenizer = AutoTokenizer.from_pretrained(general_model_id)
qa_model = AutoModelForCausalLM.from_pretrained(general_model_id)
qa_pipeline = pipeline("text-generation", model=qa_model, tokenizer=qa_tokenizer)
qa_engine = TransformersEngine(qa_pipeline)
qa_agent = CodeAgent(tools=[], llm_engine=qa_engine)

# 2. Wrap domain agents as ManagedAgents
managed_med_agent = ManagedAgent(
    agent=med_agent,
    name="medical_qa",
    description="Handles medical and health-related questions."
)
managed_qa_agent = ManagedAgent(
    agent=qa_agent,
    name="general_qa",
    description="Handles general knowledge and non-medical questions."
)

# 3. Create the manager/router agent
manager_agent = ReactCodeAgent(
    tools=[],
    llm_engine=router_engine,
    managed_agents=[managed_med_agent, managed_qa_agent]
)

# 4. Use the system
def ask(query):
    response = manager_agent.run(query)
    print("Response:", response)

# Example queries
ask("What are the symptoms of diabetes?")
ask("Who won the World Cup in 2022?")
