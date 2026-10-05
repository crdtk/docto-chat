"""Model management: loading, lifecycle, thread-safe access."""

from transformers import AutoTokenizer, AutoModelForCausalLM, PreTrainedTokenizer, PreTrainedModel
import threading, sys, os
from typing import Optional
from server.logging_config import setup_logging

logger = setup_logging(__name__)

class ModelManager:
    """Manages LLM model and tokenizer lifecycle.

    Handles loading from HuggingFace, device placement, and thread-safe access
    to the model and tokenizer for concurrent requests.

    Attributes:
        model_name: HuggingFace model ID
        device: PyTorch device ("cpu", "cuda", etc.)
        lock: Thread lock for serializing model access
        tokenizer: HuggingFace tokenizer instance
        model: HuggingFace model instance
    """

    def __init__(self, model_name: Optional[str] = None, device: str = "cpu") -> None:
        """Initialize and load model.

        Args:
            model_name: HuggingFace model ID (default from MODEL_NAME env var)
            device: PyTorch device for model placement (default: "cpu")
        """
        self.model_name: str = model_name or os.getenv("MODEL_NAME", "prav-974/medical-qa-tinyllama")
        self.device: str = device
        self.lock: threading.Lock = threading.Lock()
        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.model: Optional[PreTrainedModel] = None
        self.load()

    def load(self) -> None:
        """Load tokenizer and model from HuggingFace with optional quantization.

        Raises:
            SystemExit: If model loading fails
        """
        logger.info(f"Loading model (first time ~2-5 minutes)...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # Check if quantization is enabled
            quantize = os.getenv("QUANTIZE", "false").lower() == "true"

            if quantize:
                try:
                    from transformers import BitsAndBytesConfig
                    # 8-bit quantization reduces memory by ~50% with minimal accuracy loss
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        device_map="auto"
                    )
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        quantization_config=quantization_config
                    )
                    logger.info(f"✓ Model loaded with 8-bit quantization: {self.model_name}")
                except ImportError:
                    logger.warning("bitsandbytes not available, falling back to full precision")
                    self.model = AutoModelForCausalLM.from_pretrained(self.model_name).to(self.device)
                    logger.info(f"✓ Model loaded: {self.model_name}")
            else:
                self.model = AutoModelForCausalLM.from_pretrained(self.model_name).to(self.device)
                logger.info(f"✓ Model loaded: {self.model_name}")

            self.warmup()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            sys.exit(1)

    def warmup(self) -> None:
        """Warm up model with dummy generation.

        Eliminates slow first request by pre-populating caches.
        """
        try:
            logger.info("Warming up model...")
            prompt = "Hello"
            inputs = self.tokenizer(prompt, return_tensors="pt")
            self.model.generate(**inputs, max_new_tokens=5)
            logger.info("✓ Model warmed up")
        except Exception as e:
            logger.warning(f"Model warmup failed (non-critical): {e}")
