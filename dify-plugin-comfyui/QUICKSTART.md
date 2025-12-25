# Quick Start Guide

## 🚀 Quick Installation

### Option 1: Install from GitHub (Recommended)

1. Open your Dify instance
2. Go to **Settings** → **Plugins**
3. Click **Install from GitHub**
4. Enter: `https://github.com/yourusername/dify-plugin-comfyui`
5. Click **Install**

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/dify-plugin-comfyui.git
cd dify-plugin-comfyui

# Install dependencies
pip install -r requirements.txt

# Configure debug environment
cp .env.example .env
# Edit .env with your Dify debug credentials

# Run in debug mode
python -m main
```

## ⚙️ Configuration

After installation, configure the plugin:

1. Go to **Plugin Settings**
2. Find **ComfyUI** plugin
3. Enter your **ComfyUI Base URL**:
   - Local: `http://localhost:8188`
   - Load Balancer: `http://your-lb-url:8100`
   - Remote: `http://your-comfyui-server:8188`
4. Click **Save**

## 📝 Basic Usage

### In Dify Workflow

1. Create a new Workflow
2. Add a **Tool** node
3. Select **ComfyUI** → **Generate Image**
4. Connect a text input with your workflow API JSON
5. Run the workflow

### Example Workflow API

```json
{
  "3": {
    "inputs": {
      "seed": 156680208700286,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {
      "text": "beautiful landscape, mountains, sunset",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "text, watermark, low quality",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "8": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    },
    "class_type": "VAEDecode"
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  }
}
```

## 🔧 Getting Your Workflow API

### From ComfyUI:

1. Create your workflow in ComfyUI
2. Click **Save (API Format)**
3. Copy the JSON
4. Use it in Dify

### Tips:

- Make sure your workflow has a **SaveImage** node
- The workflow must be valid and complete
- All required models must be available in your ComfyUI instance

## 🎯 Common Use Cases

### 1. Text-to-Image Generation

```
User Input → LLM (generates workflow) → ComfyUI Tool → Image Output
```

### 2. Image Variation

```
Upload Image → Process → ComfyUI Tool → Variation Output
```

### 3. Batch Generation

```
Loop Node → ComfyUI Tool → Collect Images
```

## ❓ Troubleshooting

### Plugin Installation Failed

- Check if the GitHub URL is correct
- Ensure you have internet connection
- Verify Dify version compatibility (v0.6.0+)

### Connection Error

- Verify ComfyUI is running
- Check the base URL is accessible
- Test with: `curl http://your-comfyui-url/queue`

### Image Not Generated

- Check ComfyUI logs for errors
- Verify workflow JSON is valid
- Ensure all models are available
- Check timeout settings (default: 5 minutes)

### Workflow API Invalid

- Validate JSON syntax
- Export from ComfyUI in API format
- Check all node connections are correct

## 📚 Next Steps

- Read the full [README.md](README.md)
- Check [examples/](examples/) for more workflows
- See [PUBLISHING.md](PUBLISHING.md) for contribution guide
- Join [Dify Community](https://community.dify.ai) for support

## 🆘 Get Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/dify-plugin-comfyui/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/dify-plugin-comfyui/discussions)
- **Community**: [Dify Discord](https://discord.gg/dify)

---

**Happy Image Generating! 🎨**
