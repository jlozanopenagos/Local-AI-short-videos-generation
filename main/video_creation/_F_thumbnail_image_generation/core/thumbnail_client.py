import json
import logging
import random
import time
import shutil
from pathlib import Path
from typing import Any

import requests
try:
    from _C_image_generation.core.comfy_client import ImageComfyClient
except ImportError:
    from video_creation._C_image_generation.core.comfy_client import ImageComfyClient

logger = logging.getLogger(__name__)

# Node IDs for flux1_dev_uso_reference_image_gen.json (API format)
_NODE_POSITIVE_PROMPT = "112:6"
_NODE_KSAMPLER        = "112:31"
_NODE_SAVE_IMAGE      = "9"
_NODE_LATENT_IMAGE    = "112:110"
_NODE_LOAD_IMAGE      = "47"


class ThumbnailComfyClient(ImageComfyClient):
    """
    ComfyUI client tailored for the Flux Reference Image workflow.
    """
    def __init__(
        self,
        api_url: str,
        workflow_path: Path,
        comfy_input_dir: Path,
        poll_timeout: int = 600,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(api_url, workflow_path, poll_timeout, poll_interval)
        self.comfy_input_dir = comfy_input_dir

    def _prepare_workflow(
        self,
        prompt_text: str,
        filename_prefix: str,
        reference_image_name: str,
        seed: int,
        steps: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        
        # We don't use self._api_template because it was converted. 
        # But wait, the file is ALREADY in API format. 
        # We just load the json as is.
        with self.workflow_path.open("r", encoding="utf-8") as fh:
            wf = json.load(fh)

        # Inject positive prompt text
        if _NODE_POSITIVE_PROMPT in wf:
            wf[_NODE_POSITIVE_PROMPT]["inputs"]["text"] = prompt_text
        else:
            logger.warning(f"Positive prompt node '{_NODE_POSITIVE_PROMPT}' not found.")

        # Inject seed and steps into KSampler
        if _NODE_KSAMPLER in wf:
            wf[_NODE_KSAMPLER]["inputs"]["seed"] = seed
            wf[_NODE_KSAMPLER]["inputs"]["steps"] = steps
            
        # Inject dimensions into LatentImage
        if _NODE_LATENT_IMAGE in wf:
            wf[_NODE_LATENT_IMAGE]["inputs"]["width"] = width
            wf[_NODE_LATENT_IMAGE]["inputs"]["height"] = height

        # Inject filename prefix into SaveImage
        if _NODE_SAVE_IMAGE in wf:
            wf[_NODE_SAVE_IMAGE]["inputs"]["filename_prefix"] = filename_prefix

        # Inject Reference Image
        if _NODE_LOAD_IMAGE in wf:
            wf[_NODE_LOAD_IMAGE]["inputs"]["image"] = reference_image_name

        return wf

    def generate_thumbnail(
        self,
        prompt_text: str,
        filename_prefix: str,
        dest_path: Path,
        reference_image_path: Path,
        seed: int | None = None,
        steps: int = 20,
        width: int = 576,
        height: int = 1024,
    ) -> Path:
        
        if seed is None:
            seed = random.randint(1, 10**15)
            
        # 1. Copy reference image to ComfyUI input directory
        # Use a consistent name or unique name
        ref_name = f"ref_{reference_image_path.name}"
        comfy_input_path = self.comfy_input_dir / ref_name
        shutil.copy2(reference_image_path, comfy_input_path)

        wf = self._prepare_workflow(
            prompt_text=prompt_text,
            filename_prefix=filename_prefix,
            reference_image_name=ref_name,
            seed=seed,
            steps=steps,
            width=width,
            height=height,
        )

        prompt_id = self._queue_prompt(wf)
        history = self._poll_for_completion(prompt_id)

        filename, subfolder, file_type = self._find_image_output(history)
        self._download_image(filename, subfolder, file_type, dest_path)

        # Clean up the reference image from ComfyUI input folder
        try:
            if comfy_input_path.exists():
                comfy_input_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete reference image {comfy_input_path}: {e}")

        return dest_path
