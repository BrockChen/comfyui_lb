# Dify ComfyUI Plugin - Project Structure

## 📁 Directory Structure

```
dify-plugin-comfyui/
├── _assets/
│   └── icon.svg                 # Plugin icon (node-based design)
├── examples/
│   └── basic_workflow.json      # Example ComfyUI workflow API
├── provider/
│   ├── comfyui.yaml            # Provider configuration
│   └── comfyui.py              # Provider implementation with validation
├── tools/
│   ├── generate_image.yaml     # Tool configuration
│   └── generate_image.py       # Tool implementation (async)
├── .env.example                # Environment template for debugging
├── .gitignore                  # Git ignore rules
├── CHANGELOG.md                # Version history
├── LICENSE                     # MIT License
├── PUBLISHING.md               # Publishing guide
├── QUICKSTART.md               # Quick start guide
├── README.md                   # Main documentation
├── __init__.py                 # Package initialization
├── main.py                     # Plugin entry point
├── manifest.yaml               # Plugin manifest
├── requirements.txt            # Python dependencies
└── validate.py                 # Structure validation script
```

## 🎯 Key Features

### 1. Workflow API Integration
- Accepts ComfyUI workflow API in JSON format
- Supports all ComfyUI node types
- Automatic parameter handling

### 2. Image Generation
- Async processing with httpx
- Polling-based completion detection
- Automatic image download
- Dify blob storage integration

### 3. Load Balancer Support
- Compatible with ComfyUI load balancer
- Backend routing support
- Automatic backend detection

### 4. Error Handling
- Comprehensive error messages
- Timeout protection (5 minutes default)
- Connection validation
- JSON validation

### 5. Dify Integration
- Proper file storage using blob API
- Progress reporting
- Tool parameter validation
- Credential management

## 🔧 Technical Details

### Provider (comfyui.py)
- Validates ComfyUI connection on credential save
- Tests `/queue` endpoint for health check
- Raises `ToolProviderCredentialValidationError` on failure

### Tool (generate_image.py)
- Async image generation with `asyncio`
- Uses `httpx.AsyncClient` for HTTP requests
- Implements polling with 2-second intervals
- Returns image as blob with proper MIME type

### Configuration
- **manifest.yaml**: Plugin metadata and version
- **provider/comfyui.yaml**: Credential schema
- **tools/generate_image.yaml**: Tool parameters

## 📊 Data Flow

```
User Input (Workflow API JSON)
    ↓
Dify Tool Node
    ↓
Plugin Validation
    ↓
Submit to ComfyUI (/prompt)
    ↓
Poll for Completion (/history/{prompt_id})
    ↓
Download Image (/view)
    ↓
Return Blob to Dify
    ↓
Store in Dify File System
```

## 🚀 Deployment Options

### 1. GitHub Installation
- Push to GitHub repository
- Users install via GitHub URL
- Automatic updates on new releases

### 2. Dify Marketplace
- Submit PR to dify-plugins repository
- Review and approval process
- Listed in official marketplace

### 3. Local Development
- Use `.env` for debug credentials
- Run `python -m main` for testing
- Hot reload during development

## ✅ Validation Checklist

Run `python validate.py` to check:
- [x] All required files present
- [x] YAML syntax valid
- [x] JSON examples valid
- [x] Python syntax correct
- [x] Icon file exists
- [x] Documentation complete

## 🔐 Security Considerations

1. **Credentials**: Stored securely in Dify
2. **API Keys**: Never committed to repository
3. **URLs**: Validated before use
4. **Timeouts**: Prevent indefinite hanging
5. **Error Messages**: Don't expose sensitive info

## 📝 Customization Guide

### Adding New Parameters

1. Edit `tools/generate_image.yaml`:
```yaml
parameters:
  - name: your_parameter
    type: string
    required: false
    label:
      en_US: Your Parameter
```

2. Update `tools/generate_image.py`:
```python
param_value = tool_parameters.get('your_parameter', 'default')
```

### Changing Timeout

In `generate_image.py`:
```python
async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes
```

### Custom Error Messages

In `generate_image.py`:
```python
yield self.create_text_message("Your custom error message")
```

## 🧪 Testing

### Manual Testing
1. Configure ComfyUI URL
2. Use example workflow from `examples/`
3. Check image generation
4. Verify error handling

### Automated Testing
```bash
python validate.py  # Structure validation
python -m pytest    # Unit tests (if added)
```

## 📦 Packaging

```bash
# Install Dify CLI
pip install dify-plugin

# Package plugin
dify plugin package ./dify-plugin-comfyui

# Output: comfyui.difypkg
```

## 🌟 Best Practices

1. **Version Control**: Use semantic versioning
2. **Documentation**: Keep README updated
3. **Examples**: Provide working workflows
4. **Error Handling**: Clear, actionable messages
5. **Testing**: Validate before each release

## 🔄 Update Process

1. Make changes to code
2. Update version in `manifest.yaml`
3. Update `CHANGELOG.md`
4. Run `python validate.py`
5. Test locally
6. Commit and push
7. Create GitHub release
8. Users auto-update

## 📞 Support Channels

- GitHub Issues: Bug reports
- GitHub Discussions: Questions
- Dify Community: General help
- Documentation: README, QUICKSTART

---

**Plugin Status**: ✅ Ready for Production

**Last Validated**: 2025-12-21

**Validation Result**: All checks passed
