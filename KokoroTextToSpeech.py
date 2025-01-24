import comfy.sample as comfy_sample
import numpy as np
import torch
from kokoro_onnx import Kokoro
import logging
import os
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)



AVAILABLE_SPEAKERS = [
    "af",
    "af_sarah",
    "af_bella",
    "af_nicole",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
]

class KokoroTextToSpeech:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {}),  # Removed multiline and default to make it a parameter input
                "speaker": (AVAILABLE_SPEAKERS, {"default": "af_sarah"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "kokoro"

    def __init__(self):
        self.kokoro = None
        logger.info("Initializing KokoroTextToSpeech class.")
        # Get the directory where this file is located
        self.node_dir = os.path.dirname(os.path.abspath(__file__))
        comfy_path = os.path.dirname(os.path.dirname(self.node_dir))
        models_path = os.path.join(comfy_path, "models", "Kokorotts")
        self.model_path = os.path.join(models_path, "kokoro-v0_19.onnx")
        self.voices_path = os.path.join(models_path, "voices.json")

    def _check_files_exist(self):
        """Check if required model and voice files exist"""
        if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
            logger.error(
                f"ERROR: model or voice file not found. Please download them manually from "
                f"Model and Voices place them in the ComfyUI/models/Kokorotts folder. "
                f"model_path: {self.model_path}, voices_path: {self.voices_path}"
            )
            return False
        return True

    def _initialize_kokoro(self):
        """Initialize Kokoro TTS engine"""
        try:
            return Kokoro(model_path=self.model_path, voices_path=self.voices_path)
        except Exception as e:
            logger.error(f"ERROR: could not load kokoro-onnx in generate: {e}")
            return None

    def _create_audio(self, kokoro, text, speaker):
        """Generate audio from text"""
        try:
            return kokoro.create(text, voice=speaker, speed=1.0, lang="en-us")
        except Exception as e:
            logger.error(f"ERROR: could not generate speech using kokoro.create. Error: {e}")
            return None, None

    def generate(self, text, speaker):
        if not self._check_files_exist():
            return (None,)

        kokoro = self._initialize_kokoro()
        if not kokoro:
            return (None,)

        audio, sample_rate = self._create_audio(kokoro, text, speaker)
        if audio is None:
            logger.error("ERROR: the text-to-speech generation did not return audio. Make sure you have a valid text string.")
            return (None,)

        # Convert the numpy array to the format expected by comfy audio output
        audio_tensor = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0).float()

        logger.info(f"Successfully generated audio. Audio shape: {audio_tensor.shape}. Audio length: {len(audio)}")
        return ({"waveform": audio_tensor, "sample_rate": sample_rate},)

    @classmethod
    def IS_CHANGED(cls, text, speaker):
        return hash((text, speaker))

NODE_CLASS_MAPPINGS = {
    "Kokoro TextToSpeech": KokoroTextToSpeech,
}