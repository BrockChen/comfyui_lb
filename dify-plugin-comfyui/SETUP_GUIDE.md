# Dify ComfyUI Plugin - Complete Setup Guide

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ Dify instance (v0.6.0 or higher)
- ✅ ComfyUI instance (running and accessible)
- ✅ Python 3.10+ (for local development)
- ✅ Git (for version control)

## 🎯 Installation Methods

### Method 1: Install from GitHub (Production)

**Step 1**: Publish to GitHub

```bash
# Initialize git repository
cd dify-plugin-comfyui
git init
git add .
git commit -m "Initial commit: ComfyUI plugin for Dify"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/dify-plugin-comfyui.git
git branch -M main
git push -u origin main

# Create a release (v0.0.1)
# Go to GitHub → Releases → Create new release
```

**Step 2**: Install in Dify

1. Open Dify → **Settings** → **Plugins**
2. Click **Install from GitHub**
3. Enter: `https://github.com/YOUR_USERNAME/dify-plugin-comfyui`
4. Click **Install**
5. Wait for installation to complete

**Step 3**: Configure

1. Find **ComfyUI** in installed plugins
2. Click **Settings**
3. Enter **ComfyUI Base URL**:
   - Local: `http://localhost:8188`
   - Remote: `http://your-server-ip:8188`
   - Load Balancer: `http://your-lb-url:8100`
4. Click **Test Connection**
5. Click **Save**

### Method 2: Local Development (Testing)

**Step 1**: Setup Environment

```bash
cd dify-plugin-comfyui

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Step 2**: Configure Debug Mode

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
nano .env
```

Add your Dify debug credentials:
```
INSTALL_METHOD=remote
INSTALL_KEY=your-debug-key-from-dify
REMOTE_INSTALL_HOST=your-dify-instance-url
REMOTE_INSTALL_PORT=5003
```

**Step 3**: Run Plugin

```bash
# Validate structure
python validate.py

# Start plugin in debug mode
python -m main
```

You should see:
```
Plugin started successfully
Connected to Dify at: your-dify-instance-url
```

## 🔧 Configuration Details

### ComfyUI URL Formats

| Setup Type | URL Format | Example |
|------------|-----------|---------|
| Local ComfyUI | `http://localhost:8188` | `http://localhost:8188` |
| Remote ComfyUI | `http://IP:PORT` | `http://192.168.1.100:8188` |
| Load Balancer | `http://LB_URL:PORT` | `http://lb.example.com:8100` |
| Docker | `http://container_name:8188` | `http://comfyui:8188` |

### Testing Connection

```bash
# Test ComfyUI is accessible
curl http://your-comfyui-url:8188/queue

# Expected response:
{"queue_running": [], "queue_pending": []}
```

## 📝 Usage Examples

### Example 1: Basic Text-to-Image in Workflow

**Workflow Setup**:
1. Add **Code** node with workflow API JSON
2. Add **Tool** node → Select **ComfyUI** → **Generate Image**
3. Connect Code output to Tool input
4. Add **End** node to display image

**Workflow API** (in Code node):
```json
{
  "3": {
    "inputs": {
      "seed": 123456,
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
      "text": "beautiful landscape, mountains, sunset, highly detailed",
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

### Example 2: Dynamic Prompt with LLM

**Workflow Setup**:
1. **LLM** node → Generate workflow JSON based on user input
2. **Tool** node → ComfyUI Generate Image
3. **End** node → Display result

**LLM Prompt**:
```
Generate a ComfyUI workflow API JSON for: {user_input}
Use the following template and modify the prompt text in node "6":
{template_json}
```

### Example 3: Batch Generation

**Workflow Setup**:
1. **List** node → Multiple workflow JSONs
2. **Loop** node → Iterate through list
3. **Tool** node → ComfyUI Generate Image
4. **Collect** node → Gather all images

## 🐛 Troubleshooting

### Issue: Plugin Installation Failed

**Symptoms**: Error during GitHub installation

**Solutions**:
1. Check GitHub URL is correct and public
2. Verify `manifest.yaml` syntax
3. Ensure all required files exist
4. Check Dify logs for detailed error

```bash
# Validate plugin structure
python validate.py
```

### Issue: Connection Error

**Symptoms**: "Failed to connect to ComfyUI"

**Solutions**:
1. Verify ComfyUI is running:
   ```bash
   curl http://your-comfyui-url:8188/queue
   ```

2. Check firewall settings

3. Test from Dify server:
   ```bash
   # SSH to Dify server
   curl http://comfyui-url:8188/queue
   ```

4. Check URL format (no trailing slash)

### Issue: Workflow API Invalid

**Symptoms**: "Invalid JSON in workflow_api"

**Solutions**:
1. Validate JSON syntax:
   ```bash
   cat workflow.json | python -m json.tool
   ```

2. Export from ComfyUI in **API Format**:
   - ComfyUI → Save → **Save (API Format)**

3. Check all node IDs are strings

### Issue: Timeout

**Symptoms**: "Timeout waiting for image generation"

**Solutions**:
1. Increase timeout in `generate_image.py`:
   ```python
   async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutes
   ```

2. Check ComfyUI queue:
   ```bash
   curl http://your-comfyui-url:8188/queue
   ```

3. Verify models are loaded in ComfyUI

### Issue: Image Not Found

**Symptoms**: "No images found in output"

**Solutions**:
1. Ensure workflow has **SaveImage** node
2. Check ComfyUI output folder
3. Verify node connections in workflow
4. Check ComfyUI logs for errors

## 📊 Monitoring

### Check Plugin Status

In Dify:
1. Go to **Settings** → **Plugins**
2. Find **ComfyUI** plugin
3. Check status indicator (green = active)

### View Logs

```bash
# Dify logs
docker logs dify-api -f

# ComfyUI logs
# Check ComfyUI console output
```

### Debug Mode

Enable debug logging in `generate_image.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Performance Tips

1. **Use Load Balancer**: For high traffic
2. **Optimize Workflows**: Reduce unnecessary nodes
3. **Cache Models**: Keep models loaded in ComfyUI
4. **Adjust Timeout**: Based on your workflow complexity
5. **Monitor Resources**: CPU, GPU, Memory usage

## 📚 Additional Resources

- **Full Documentation**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Publishing Guide**: [PUBLISHING.md](PUBLISHING.md)
- **Project Structure**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **Example Workflows**: [examples/](examples/)

## 🆘 Getting Help

1. **Check Documentation**: Read all .md files
2. **Search Issues**: GitHub Issues for similar problems
3. **Ask Community**: Dify Discord/Forum
4. **Create Issue**: Provide detailed error logs

## ✅ Verification Checklist

Before considering setup complete:

- [ ] Plugin installed successfully
- [ ] ComfyUI connection tested
- [ ] Example workflow runs successfully
- [ ] Image generated and displayed
- [ ] Error handling works (test with invalid JSON)
- [ ] Documentation reviewed

---

**Setup Complete! 🎉**

You're now ready to generate images with ComfyUI through Dify!
