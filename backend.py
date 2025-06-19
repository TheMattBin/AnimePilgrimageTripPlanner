from typing import Literal, TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langchain_core.messages import BaseMessage, HumanMessage
from vllm import LLM, SamplingParams  # Using vLLM instead of proprietary APIs

# Define state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + [y]]

# Initialize vLLM models with Hugging Face integration
supervisor_llm = LLM(
    model="Qwen/Qwen1.5-0.5B",  # Lightweight routing model
    dtype="bfloat16",
    tensor_parallel_size=1
)

medical_llm = LLM(
    model="medicalai/Qwen-Med",  # Medical specialized model
    dtype="bfloat16",
    tensor_parallel_size=1
)

general_llm = LLM(
    model="Qwen/Qwen1.5-7B",  # General QA model
    dtype="bfloat16",
    tensor_parallel_size=1
)

# Define agent roles
agents = ["medical_agent", "general_agent"]
options = agents + ["FINISH"]

# ======================
# Supervisor Agent Node
# ======================
def supervisor_node(state: AgentState):
    # System prompt for routing decisions
    system_prompt = f"""
    Classify user queries:
    - Medical: Symptoms, conditions, medications, health advice
    - General: Non-medical questions, facts, explanations
    Respond ONLY with: {options}
    """

    # Generate routing decision
    prompt = system_prompt + "\n\n" + state["messages"][-1].content
    sampling_params = SamplingParams(temperature=0.0, max_tokens=10)
    output = supervisor_llm.generate(prompt, sampling_params)
    next_step = output[0].outputs[0].text.strip().split()[0]
    
    print(f"Routing to: {next_step}")
    return Command(goto=next_step if next_step != "FINISH" else END)

# ======================
# Domain Agent Functions
# ======================
def run_agent(llm: LLM, state: AgentState):
    prompt = state["messages"][-1].content
    sampling_params = SamplingParams(temperature=0.7, max_tokens=500)
    output = llm.generate(prompt, sampling_params)
    return {"messages": [HumanMessage(content=output[0].outputs[0].text)]}

def medical_agent(state: AgentState):
    return run_agent(medical_llm, state)

def general_agent(state: AgentState):
    return run_agent(general_llm, state)

# ======================
# Graph Construction
# ======================
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("medical_agent", medical_agent)
workflow.add_node("general_agent", general_agent)

# Set entry point
workflow.set_entry_point("supervisor")

# Define transitions
workflow.add_edge("medical_agent", "supervisor")
workflow.add_edge("general_agent", "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["messages"][-1].content,
    {
        "medical_agent": "medical_agent",
        "general_agent": "general_agent",
        "FINISH": END
    }
)

# Compile the multi-agent system
app = workflow.compile()
