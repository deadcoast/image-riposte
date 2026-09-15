# ComfyUI Custom I2V Training Pipeline — Solo Dev Build

## Core Stack

**Training framework:** ai-toolkit (Ostris) — primary. diffusion-pipe as fallback for larger context windows.

**Base model:** Wan 2.2 I2V 14B (`Wan-AI/Wan2.2-I2V-A14B` on HuggingFace)

**Inference:** ComfyUI + ComfyUI-WanVideoWrapper (Kijai)

**Captioning:** Florence-2-large for images, CogVLM2-Video for video clips

**Dataset tooling:** ffmpeg + custom Python for bucketing

---

## Rental Machine Spec

Single H100 80GB SXM on RunPod Secure Cloud or Lambda. Non-negotiables:

- CUDA 12.4+
- 200GB+ container disk
- Persistent network volume (100GB minimum) — mount at `/workspace/persist`
- PyTorch 2.4 base template

Skip Vast.ai for training runs — spot preemption mid-training kills you. Fine for inference testing.

---

## Directory Structure on Rental

```txt
/workspace/
├── persist/                    # network volume, survives pod termination
│   ├── models/
│   │   ├── wan22_i2v_14b/     # base checkpoint
│   │   └── vae/
│   ├── datasets/
│   │   └── project_01/
│   │       ├── videos/         # .mp4 clips
│   │       ├── captions/       # .txt paired files
│   │       └── metadata.json
│   └── outputs/
│       └── loras/              # trained .safetensors files
├── ai-toolkit/
└── ComfyUI/                    # for validation inference on same pod
```

---

## Dataset Prep Pipeline

**Clip specs Wan 2.2 responds to:**

- Resolution: 720x480 or 512x512 (bucket by aspect ratio)
- Length: 33, 49, 65, or 81 frames (multiples of 16+1)
- FPS: 16 (Wan's native training rate)
- Codec: h264, yuv420p

**ffmpeg segmentation:**

```bash
ffmpeg -i source.mp4 -vf "fps=16,scale=720:480" \
  -c:v libx264 -pix_fmt yuv420p -an \
  -f segment -segment_time 3 \
  -reset_timestamps 1 clips/clip_%04d.mp4
```

**Captioning script pattern:**

```python
from transformers import AutoProcessor, AutoModelForCausalLM
import torch, os, glob

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-large",
    torch_dtype=torch.float16,
    trust_remote_code=True
).cuda()
processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-large", trust_remote_code=True
)

for clip in glob.glob("videos/*.mp4"):
    # extract middle frame, caption it, prepend action tags
    # write to captions/{basename}.txt
```

**Caption format that works for Wan I2V:**

```txt
[trigger_token], [subject description], [action/motion description], 
[camera behavior], [lighting/style]
```

Example: `wnstyle, a woman with red hair, slowly turning her head toward camera, static shot, warm golden hour lighting`

Trigger token is critical. Pick something orthogonal (`wnstyle`, `zqx7`) not a real word.

---

## ai-toolkit Config for Wan 2.2 I2V LoRA

`config/wan22_lora.yaml`:

```yaml
job: extension
config:
  name: "project_01_v1"
  process:
    - type: 'sd_trainer'
      training_folder: "/workspace/persist/outputs/loras"
      device: cuda:0
      network:
        type: "lora"
        linear: 32
        linear_alpha: 32
      save:
        dtype: float16
        save_every: 500
        max_step_saves_to_keep: 4
      datasets:
        - folder_path: "/workspace/persist/datasets/project_01"
          caption_ext: "txt"
          caption_dropout_rate: 0.05
          resolution: [512, 720]
          num_frames: 49
          fps: 16
      train:
        batch_size: 1
        steps: 3000
        gradient_accumulation_steps: 4
        train_unet: true
        train_text_encoder: false
        gradient_checkpointing: true
        noise_scheduler: "flowmatch"
        optimizer: "adamw8bit"
        lr: 1e-4
        ema_config:
          use_ema: true
          ema_decay: 0.99
        dtype: bf16
      model:
        name_or_path: "/workspace/persist/models/wan22_i2v_14b"
        is_v_pred: false
        quantize: true
      sample:
        sampler: "flowmatch"
        sample_every: 500
        width: 512
        height: 512
        prompts:
          - "wnstyle, [test prompt matching your training distribution]"
        neg: ""
        seed: 42
        walk_seed: true
        guidance_scale: 5
        sample_steps: 25
```

Key knobs:

- **linear rank 32**: good for style/subject. Bump to 64 for complex motion concepts, 16 for simple styles.
- **gradient_accumulation_steps 4**: effective batch of 4 without VRAM blowup
- **quantize: true**: loads base in 8-bit for training, keeps VRAM under 70GB
- **caption_dropout_rate 0.05**: prevents overfitting on caption structure

---

## Training Execution

```bash
cd /workspace/ai-toolkit
python run.py config/wan22_lora.yaml
```

Monitor VRAM with `watch -n 2 nvidia-smi`. If OOM, drop `num_frames` to 33 first, then reduce resolution before touching rank.

Checkpoints save to `/workspace/persist/outputs/loras/project_01_v1/`. Sample outputs generate every 500 steps into `samples/` — check these to catch overfitting early. If samples start looking identical to training data around step 1500-2000, kill it and use the earlier checkpoint.

---

## ComfyUI Inference Setup (Same Pod, for Validation)

```bash
cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt
cd custom_nodes
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper
cd ComfyUI-WanVideoWrapper && pip install -r requirements.txt
```

Symlink models:

```bash
ln -s /workspace/persist/models/wan22_i2v_14b \
  /workspace/ComfyUI/models/diffusion_models/wan22
ln -s /workspace/persist/outputs/loras/project_01_v1 \
  /workspace/ComfyUI/models/loras/project_01
```

Launch with tunnel:

```bash
python main.py --listen 0.0.0.0 --port 8188
```

Forward via RunPod's HTTP proxy or `cloudflared tunnel`.

---

## Core ComfyUI Workflow Nodes

Input → Output chain:

1. **LoadImage** (source image)
2. **WanVideoModelLoader** → base checkpoint, precision fp8_e4m3fn
3. **WanVideoLoraSelect** → your trained LoRA, strength 0.8-1.0
4. **WanVideoVAELoader**
5. **WanVideoTextEncode** → prompt with your trigger token
6. **WanVideoImageToVideoEncode** → connects image + latent space
7. **WanVideoSampler** → 25-30 steps, cfg 5-6, flowmatch scheduler
8. **WanVideoDecode** → back to pixel space
9. **VHS_VideoCombine** → mp4 output, 16fps

Save this as `.json` workflow. This becomes your API template.

---

## API Wrapper for Programmatic Access

ComfyUI exposes `/prompt` endpoint. Submission pattern:

```python
import json, requests, websocket, uuid

COMFY_URL = "http://localhost:8188"
client_id = str(uuid.uuid4())

def queue_prompt(workflow):
    p = {"prompt": workflow, "client_id": client_id}
    return requests.post(f"{COMFY_URL}/prompt", json=p).json()

def wait_for_completion(prompt_id):
    ws = websocket.WebSocket()
    ws.connect(f"ws://localhost:8188/ws?clientId={client_id}")
    while True:
        msg = json.loads(ws.recv())
        if msg["type"] == "executing":
            if msg["data"]["node"] is None and msg["data"]["prompt_id"] == prompt_id:
                break
    return requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
```

Load your saved workflow JSON, mutate the input image path and prompt fields, submit.

---

## Multi-LoRA Composition

WanVideoLoraSelect nodes chain. Stack 2-3 LoRAs max before quality degrades:

```txt
Base → LoRA_style (0.7) → LoRA_subject (0.9) → LoRA_motion (0.5) → Sampler
```

Test each strength independently before stacking. Additive artifacts compound fast.

---

## Data Sync Between Local and Rental

Use `rclone` with Backblaze B2 or R2 as intermediary:

```bash
# local → cloud
rclone sync ./dataset_local b2:mybucket/datasets/project_01

# rental pulls
rclone sync b2:mybucket/datasets/project_01 /workspace/persist/datasets/project_01

# rental pushes LoRA back
rclone sync /workspace/persist/outputs/loras b2:mybucket/loras
```

Never keep sole copies on ephemeral pod storage.

---

## Failure Modes to Preempt

**Loss plateaus at ~0.1 and stays flat**: LR too low, or dataset too homogeneous. Bump LR to 2e-4 or diversify captions.

**Samples show training data verbatim by step 2000**: overfitting. Reduce steps, increase caption_dropout_rate to 0.1, or add more data.

**LoRA has no visible effect at inference**: trigger token mismatch, or alpha too low. Verify token in captions matches inference prompt exactly.

**Motion looks jittery in output**: num_frames during training didn't match inference. Train at 49, infer at 49. Or train at 33 and interpolate with RIFE post-hoc.

**VRAM spikes at step 1**: gradient checkpointing not activating. Confirm `gradient_checkpointing: true` and restart.

---

## Iteration Loop

1. Train LoRA on rental
2. rclone LoRA to local
3. Test in local ComfyUI on 10-20 diverse source images
4. Log failures (bad motion, ignored trigger, style leak)
5. Adjust dataset — remove bad clips, recaption weak ones, add coverage for failure cases
6. Retrain from scratch (not resume — flow matching hates resumes on small datasets)

Three to five iterations gets a production-quality concept LoRA. First one is always garbage; expect it and move on.
