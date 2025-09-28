from typing import Dict, List, Optional, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import LLM
from langchain_core.outputs import LLMResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from config import Config

class LocalHuggingFaceLLM(LLM):
    """
    Custom LangChain LLM wrapper for local Hugging Face models
    """

    model_name: str
    tokenizer: Optional[Any] = None
    model: Optional[Any] = None
    pipeline: Optional[Any] = None
    device: str = "auto"
    max_length: int = 1000
    temperature: float = 0.7

    def __init__(self, model_name: str, **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Load the model and tokenizer"""
        try:
            print(f"Loading model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",
                load_in_8bit=True if torch.cuda.is_available() else False
            )

            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=self.max_length,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

            print(f"Model {self.model_name} loaded successfully!")

        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    @property
    def _llm_type(self) -> str:
        return "local_huggingface"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the model with the given prompt"""
        try:
            response = self.pipeline(prompt, **kwargs)
            generated_text = response[0]['generated_text']

            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):]

            return generated_text.strip()

        except Exception as e:
            return f"Error generating response: {str(e)}"

    def generate_prompt(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate response from a list of messages"""
        prompt = self._convert_messages_to_prompt(messages)
        response = self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
        return LLMResult(generations=[[response]])

    def _convert_messages_to_prompt(self, messages: List[Any]) -> str:
        """Convert LangChain messages to a single prompt string"""
        prompt = ""
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt += f"System: {message.content}\n"
            elif isinstance(message, HumanMessage):
                prompt += f"Human: {message.content}\n"
            elif isinstance(message, AIMessage):
                prompt += f"Assistant: {message.content}\n"

        prompt += "Assistant:"
        return prompt

class LLMManager:
    """
    Manager for handling different LLM configurations
    """

    def __init__(self):
        self.current_model = None
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize available models"""
        try:
            model_configs = [
                {"name": "microsoft/DialoGPT-medium", "description": "Medium-sized conversational model"},
                {"name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "description": "Small chat model"},
                {"name": "microsoft/DialoGPT-small", "description": "Small conversational model"},
            ]

            for config in model_configs:
                try:
                    model = LocalHuggingFaceLLM(
                        model_name=config["name"],
                        max_length=1000,
                        temperature=0.7
                    )
                    self.models[config["name"]] = {
                        "model": model,
                        "description": config["description"],
                        "loaded": True
                    }
                    print(f"Successfully loaded model: {config['name']}")

                except Exception as e:
                    print(f"Failed to load model {config['name']}: {e}")
                    self.models[config["name"]] = {
                        "model": None,
                        "description": config["description"],
                        "loaded": False,
                        "error": str(e)
                    }

            if self.models:
                first_available_model = next(
                    (name for name, data in self.models.items() if data["loaded"]),
                    None
                )
                if first_available_model:
                    self.current_model = first_available_model
                    print(f"Default model set to: {first_available_model}")

        except Exception as e:
            print(f"Error initializing models: {e}")

    def get_model(self, model_name: Optional[str] = None) -> Optional[LocalHuggingFaceLLM]:
        """Get a specific model by name"""
        if model_name is None:
            model_name = self.current_model

        if model_name and model_name in self.models:
            model_data = self.models[model_name]
            if model_data["loaded"] and model_data["model"]:
                return model_data["model"]
            else:
                print(f"Model {model_name} is not loaded properly")
                return None
        else:
            print(f"Model {model_name} not found")
            return None

    def list_available_models(self) -> Dict[str, Dict]:
        """List all available models"""
        return self.models

    def set_current_model(self, model_name: str) -> bool:
        """Set the current model"""
        if model_name in self.models and self.models[model_name]["loaded"]:
            self.current_model = model_name
            print(f"Current model set to: {model_name}")
            return True
        else:
            print(f"Cannot set model {model_name} - not available or not loaded")
            return False

    def get_model_info(self, model_name: Optional[str] = None) -> Dict:
        """Get information about a specific model"""
        if model_name is None:
            model_name = self.current_model

        if model_name and model_name in self.models:
            return self.models[model_name]
        else:
            return {"error": f"Model {model_name} not found"}

    def test_model(self, model_name: Optional[str] = None, test_prompt: str = "Hello! How are you?") -> str:
        """Test a model with a sample prompt"""
        model = self.get_model(model_name)
        if model:
            try:
                response = model.invoke(test_prompt)
                return f"Model {model_name or self.current_model} test successful!\nResponse: {response}"
            except Exception as e:
                return f"Model {model_name or self.current_model} test failed: {str(e)}"
        else:
            return f"Model {model_name or self.current_model} not available"