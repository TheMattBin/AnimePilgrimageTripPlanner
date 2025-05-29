import asyncio
import json
import base64
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum
from PIL import Image
import torch
from transformers import (
    AutoProcessor, AutoModelForCausalLM, 
    LlavaNextProcessor, LlavaNextForConditionalGeneration,
    Qwen2VLForConditionalGeneration, Qwen2VLProcessor
)
import io
import requests

class AgentType(Enum):
    MEDICAL = "medical"
    MATH = "math" 
    PHYSICS = "physics"
    GENERAL = "general"

@dataclass
class QueryClassification:
    agent_type: AgentType
    confidence: float
    reasoning: str

@dataclass
class MultimodalQuery:
    text: Optional[str] = None
    images: Optional[List[Image.Image]] = None
    
    def has_text(self) -> bool:
        return self.text is not None and self.text.strip() != ""
    
    def has_images(self) -> bool:
        return self.images is not None and len(self.images) > 0
    
    def is_multimodal(self) -> bool:
        return self.has_text() and self.has_images()

class MultimodalLLMAgent:
    def __init__(self, name: str, system_prompt: str, model_name: str = "llava-hf/llava-v1.6-mistral-7b-hf"):
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load the multimodal model and processor"""
        try:
            if "llava" in self.model_name.lower():
                self.processor = LlavaNextProcessor.from_pretrained(self.model_name)
                self.model = LlavaNextForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None
                )
            elif "qwen2-vl" in self.model_name.lower():
                self.processor = Qwen2VLProcessor.from_pretrained(self.model_name)
                self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None
                )
            else:
                # Fallback to generic multimodal model
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None
                )
            
            print(f"✅ Loaded {self.name} with model: {self.model_name}")
            
        except Exception as e:
            print(f"❌ Error loading model {self.model_name}: {str(e)}")
            # Fallback to a smaller model
            self.model_name = "llava-hf/llava-1.5-7b-hf"
            self._load_model()
    
    def _prepare_messages(self, query: MultimodalQuery, context: Optional[Dict] = None) -> List[Dict]:
        """Prepare messages for the model"""
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # Add context if provided
        if context:
            context_text = f"Context: {json.dumps(context, indent=2)}"
            messages.append({
                "role": "system", 
                "content": context_text
            })
        
        # Prepare user message
        user_content = []
        
        # Add images if present
        if query.has_images():
            for img in query.images:
                user_content.append({
                    "type": "image",
                    "image": img
                })
        
        # Add text if present
        if query.has_text():
            user_content.append({
                "type": "text",
                "text": query.text
            })
        elif not query.has_text() and query.has_images():
            # If only images, add a default question
            user_content.append({
                "type": "text", 
                "text": "Analyze this image and provide relevant information."
            })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    async def process(self, query: MultimodalQuery, context: Optional[Dict] = None) -> str:
        """Process a multimodal query"""
        try:
            # Prepare conversation
            messages = self._prepare_messages(query, context)
            
            # Apply chat template
            if hasattr(self.processor, 'apply_chat_template'):
                prompt = self.processor.apply_chat_template(
                    messages, 
                    tokenize=False, 
                    add_generation_prompt=True
                )
            else:
                # Fallback prompt construction
                prompt = self._construct_prompt(messages)
            
            # Prepare inputs
            if query.has_images():
                inputs = self.processor(
                    images=query.images,
                    text=prompt,
                    return_tensors="pt"
                ).to(self.device)
            else:
                inputs = self.processor(
                    text=prompt,
                    return_tensors="pt"
                ).to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # Decode response
            generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
            response = self.processor.decode(generated_tokens, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            return f"Error processing multimodal query: {str(e)}"
    
    def _construct_prompt(self, messages: List[Dict]) -> str:
        """Fallback prompt construction"""
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if isinstance(content, str):
                prompt_parts.append(f"{role.capitalize()}: {content}")
            elif isinstance(content, list):
                text_parts = [item["text"] for item in content if item["type"] == "text"]
                if text_parts:
                    prompt_parts.append(f"{role.capitalize()}: {' '.join(text_parts)}")
        
        return "\n".join(prompt_parts) + "\nAssistant:"

class MultimodalCentralRouter(MultimodalLLMAgent):
    def __init__(self, model_name: str = "llava-hf/llava-v1.6-mistral-7b-hf"):
        system_prompt = """You are a central routing agent that analyzes user queries (which may include text, images, or both) and determines which specialized agent should handle them.

Available agents:
- MEDICAL: For health, medicine, symptoms, treatments, anatomy, diseases, medical images (X-rays, scans, etc.)
- MATH: For mathematical problems, calculations, equations, statistics, mathematical diagrams, graphs
- PHYSICS: For physics concepts, mechanics, thermodynamics, electromagnetism, physics diagrams, experimental setups
- GENERAL: For general knowledge, conversation, and queries that don't fit other categories

Analyze the user's query (text and/or images) and respond with ONLY a JSON object:
{
    "agent_type": "medical|math|physics|general",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation considering both text and visual content"
}

Consider the content, context, and visual elements to make the best routing decision."""

        super().__init__("Multimodal Router", system_prompt, model_name)
    
    async def classify_query(self, query: MultimodalQuery) -> QueryClassification:
        response = await self.process(query)
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            
            return QueryClassification(
                agent_type=AgentType(result["agent_type"]),
                confidence=float(result["confidence"]),
                reasoning=result["reasoning"]
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback classification based on simple heuristics
            return self._fallback_classification(query, str(e))
    
    def _fallback_classification(self, query: MultimodalQuery, error: str) -> QueryClassification:
        """Fallback classification when JSON parsing fails"""
        if query.has_text():
            text = query.text.lower()
            if any(word in text for word in ['medical', 'health', 'symptom', 'disease', 'doctor']):
                return QueryClassification(AgentType.MEDICAL, 0.6, "Fallback: medical keywords detected")
            elif any(word in text for word in ['math', 'calculate', 'equation', 'solve']):
                return QueryClassification(AgentType.MATH, 0.6, "Fallback: math keywords detected")
            elif any(word in text for word in ['physics', 'force', 'energy', 'motion']):
                return QueryClassification(AgentType.PHYSICS, 0.6, "Fallback: physics keywords detected")
        
        return QueryClassification(
            agent_type=AgentType.GENERAL,
            confidence=0.4,
            reasoning=f"Fallback due to classification error: {error}"
        )

class MultimodalAgentSystem:
    def __init__(self, router_model: str = "llava-hf/llava-v1.6-mistral-7b-hf", 
                 agent_model: str = "llava-hf/llava-v1.6-mistral-7b-hf"):
        self.router = MultimodalCentralRouter(router_model)
        self.agents = self._initialize_agents(agent_model)
        self.conversation_history = []
    
    def _initialize_agents(self, model_name: str) -> Dict[AgentType, MultimodalLLMAgent]:
        return {
            AgentType.MEDICAL: MultimodalLLMAgent(
                "Medical Vision Specialist",
                """You are a medical AI assistant with expertise in healthcare, medicine, anatomy, diseases, treatments, and medical imaging analysis.
                You can analyze medical images, X-rays, scans, and provide information about symptoms and conditions.
                Always recommend consulting healthcare professionals for serious medical concerns.
                Provide thorough but accessible explanations for both text queries and image analysis.""",
                model_name
            ),
            AgentType.MATH: MultimodalLLMAgent(
                "Math Vision Specialist", 
                """You are a mathematics expert capable of solving problems and analyzing mathematical content in both text and images.
                You can read mathematical notation, analyze graphs, geometric figures, and solve problems across all areas of mathematics.
                Provide step-by-step solutions and clear explanations. Show your work and reasoning.""",
                model_name
            ),
            AgentType.PHYSICS: MultimodalLLMAgent(
                "Physics Vision Specialist",
                """You are a physics expert with deep knowledge across all physics domains and the ability to analyze physics-related images.
                You can interpret experimental setups, diagrams, force diagrams, circuit diagrams, and physics phenomena in images.
                Explain concepts clearly with examples and provide relevant equations when appropriate.""",
                model_name
            ),
            AgentType.GENERAL: MultimodalLLMAgent(
                "General Vision Assistant",
                """You are a helpful multimodal AI assistant capable of understanding and analyzing both text and images.
                Provide informative, accurate, and helpful responses to a wide variety of questions and image analysis tasks.
                Be conversational and adapt your communication style to the user's needs.""",
                model_name
            )
        }
    
    def create_query(self, text: Optional[str] = None, 
                    images: Optional[List[Union[str, Image.Image]]] = None) -> MultimodalQuery:
        """Create a multimodal query from text and/or images"""
        processed_images = []
        
        if images:
            for img in images:
                if isinstance(img, str):
                    # Handle image paths or URLs
                    if img.startswith(('http://', 'https://')):
                        # URL
                        response = requests.get(img)
                        processed_images.append(Image.open(io.BytesIO(response.content)))
                    else:
                        # File path
                        processed_images.append(Image.open(img))
                elif isinstance(img, Image.Image):
                    processed_images.append(img)
        
        return MultimodalQuery(text=text, images=processed_images if processed_images else None)
    
    async def process_query(self, query: MultimodalQuery) -> Dict[str, Any]:
        """Process a multimodal query through the agent system"""
        # Step 1: Route the query
        print(f"🔍 Routing query: {'Text: ' + (query.text[:50] + '...' if query.text and len(query.text) > 50 else query.text or 'None')}")
        print(f"📷 Images: {len(query.images) if query.images else 0}")
        
        classification = await self.router.classify_query(query)
        
        # Step 2: Get specialized response
        specialized_agent = self.agents[classification.agent_type]
        
        # Create context from recent conversation history
        context = {
            "conversation_history": self.conversation_history[-2:],
            "classification": {
                "agent_type": classification.agent_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning
            }
        }
        
        print(f"🎯 Routed to: {classification.agent_type.value} (confidence: {classification.confidence:.2f})")
        
        response = await specialized_agent.process(query, context)
        
        # Step 3: Log the interaction
        interaction = {
            "query_text": query.text,
            "has_images": query.has_images(),
            "image_count": len(query.images) if query.images else 0,
            "classification": classification,
            "agent_used": classification.agent_type.value,
            "response": response
        }
        self.conversation_history.append(interaction)
        
        return {
            "query": query,
            "routed_to": classification.agent_type.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "response": response,
            "agent_name": specialized_agent.name
        }
    
    async def process_text_query(self, text: str) -> Dict[str, Any]:
        """Convenience method for text-only queries"""
        query = self.create_query(text=text)
        return await self.process_query(query)
    
    async def process_image_query(self, images: List[Union[str, Image.Image]], 
                                 text: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method for image queries"""
        query = self.create_query(text=text, images=images)
        return await self.process_query(query)

# Example usage and testing
async def main():
    print("🚀 Initializing Multimodal Agent System...")
    
    # Initialize with smaller models for demo (you can use larger ones)
    system = MultimodalAgentSystem(
        router_model="llava-hf/llava-1.5-7b-hf",
        agent_model="llava-hf/llava-1.5-7b-hf"
    )
    
    print("\n🤖 Multimodal Agent System Ready!\n" + "="*60)
    
    # Test cases
    test_cases = [
        # Text-only queries
        {
            "type": "text",
            "text": "What are the symptoms of pneumonia?",
            "images": None
        },
        {
            "type": "text", 
            "text": "Solve for x: 3x^2 + 2x - 1 = 0",
            "images": None
        },
        {
            "type": "text",
            "text": "Explain quantum entanglement",
            "images": None
        },
        # You can add image test cases here
        # {
        #     "type": "multimodal",
        #     "text": "What do you see in this medical scan?",
        #     "images": ["path/to/xray.jpg"]
        # }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['type']}")
        print(f"Text: {test_case['text']}")
        
        if test_case['images']:
            print(f"Images: {test_case['images']}")
            query = system.create_query(text=test_case['text'], images=test_case['images'])
        else:
            query = system.create_query(text=test_case['text'])
        
        result = await system.process_query(query)
        
        print(f"🎯 Routed to: {result['routed_to']} (confidence: {result['confidence']:.2f})")
        print(f"💭 Reasoning: {result['reasoning']}")
        print(f"🤖 Agent: {result['agent_name']}")
        print(f"💬 Response: {result['response'][:300]}{'...' if len(result['response']) > 300 else ''}")
        print("-" * 60)

if __name__ == "__main__":
    # Install required packages:
    # pip install torch transformers pillow requests accelerate
    asyncio.run(main())
