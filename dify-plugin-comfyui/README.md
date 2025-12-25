# Dify ComfyUI Plugin

A Dify plugin that integrates ComfyUI for AI image generation through workflow API.

## Features

- 🎨 Generate images using ComfyUI workflow API
- 🔄 Support for ComfyUI load balancer
- 📦 Automatic image download and storage in Dify
- ⚡ Async processing with progress tracking
- 🔌 Easy integration with Dify workflows and agents

## Installation

### From GitHub (Recommended)

1. Go to your Dify instance's plugin management page
2. Click "Install from GitHub"
3. Enter the repository URL: `https://github.com/yourusername/dify-plugin-comfyui`
4. Click Install

### Manual Installation

1. Clone this repository
2. Package the plugin:
   ```bash
   dify plugin package ./dify-plugin-comfyui
   ```
3. Upload the generated `.difypkg` file to your Dify instance

## Configuration

After installation, you need to configure the plugin with your ComfyUI instance:

1. Go to Plugin Settings
2. Enter your ComfyUI Base URL (e.g., `http://localhost:8188` or your load balancer URL)
3. Save the configuration

## Usage

### In Dify Workflow

1. Add a "Tool" node to your workflow
2. Select "ComfyUI" → "Generate Image"
3. Provide the workflow API JSON as input
4. The generated image will be available as the node's output

### In Dify Agent

The agent can automatically call this tool when image generation is needed. Simply provide the workflow API JSON in the conversation.

### Workflow API Format

The workflow API should be a valid ComfyUI workflow JSON. Example:

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
  ...
}
```

## Development

### Prerequisites

- Python 3.10+
- Dify Plugin CLI
- ComfyUI instance (local or remote)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dify-plugin-comfyui.git
   cd dify-plugin-comfyui
   ```

2. Copy `.env.example` to `.env` and fill in your debug credentials:
   ```bash
   cp .env.example .env
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run in debug mode:
   ```bash
   python -m main
   ```

### Testing

Test the plugin with your ComfyUI instance:

```python
import asyncio
from tools.generate_image import GenerateImageTool

# Your workflow API JSON
workflow_api = {...}

# Test the tool
tool = GenerateImageTool()
result = tool._invoke({
    'workflow_api': json.dumps(workflow_api)
})
```

## Architecture

The plugin consists of:

- **Provider** (`provider/comfyui.py`): Handles credential validation and ComfyUI connection
- **Tool** (`tools/generate_image.py`): Implements the image generation logic
- **Configuration** (`*.yaml`): Defines plugin metadata and parameters

### Image Generation Flow

1. Accept workflow API JSON from Dify
2. Submit prompt to ComfyUI with unique client ID
3. Poll for completion using history API
4. Download generated image
5. Return image blob to Dify for storage

## Compatibility

- Dify: v0.6.0+
- ComfyUI: Latest stable version
- Supports ComfyUI load balancer

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/dify-plugin-comfyui/issues
- Dify Community: https://community.dify.ai

## Acknowledgments

- [Dify](https://dify.ai) - The AI application platform
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - The powerful Stable Diffusion GUI
