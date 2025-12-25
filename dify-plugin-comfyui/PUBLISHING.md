# Publishing to GitHub and Dify Marketplace

## Prerequisites

1. GitHub account
2. Git installed locally
3. Dify account (for marketplace submission)

## Step 1: Prepare Your Repository

1. Create a new repository on GitHub:
   ```
   Repository name: dify-plugin-comfyui
   Description: ComfyUI integration plugin for Dify
   Public repository
   ```

2. Initialize git in your plugin directory:
   ```bash
   cd dify-plugin-comfyui
   git init
   git add .
   git commit -m "Initial commit: ComfyUI plugin for Dify"
   ```

3. Add remote and push:
   ```bash
   git remote add origin https://github.com/yourusername/dify-plugin-comfyui.git
   git branch -M main
   git push -u origin main
   ```

## Step 2: Create a Release

1. Go to your GitHub repository
2. Click on "Releases" → "Create a new release"
3. Tag version: `v0.0.1`
4. Release title: `v0.0.1 - Initial Release`
5. Description:
   ```markdown
   ## Features
   - Generate images using ComfyUI workflow API
   - Support for ComfyUI load balancer
   - Automatic image download and storage
   
   ## Installation
   Install directly from GitHub in Dify's plugin marketplace.
   ```
6. Click "Publish release"

## Step 3: Test Installation from GitHub

1. Go to your Dify instance
2. Navigate to Plugin Management
3. Click "Install from GitHub"
4. Enter: `https://github.com/yourusername/dify-plugin-comfyui`
5. Click Install
6. Configure with your ComfyUI URL

## Step 4: Submit to Dify Marketplace (Optional)

1. Fork the [Dify Plugins Repository](https://github.com/langgenius/dify-plugins)

2. Add your plugin:
   ```bash
   git clone https://github.com/yourusername/dify-plugins.git
   cd dify-plugins
   git checkout -b add-comfyui-plugin
   ```

3. Create a marketplace entry in `marketplace/comfyui/`:
   - Copy your plugin files
   - Ensure all metadata is correct
   - Test locally

4. Create Pull Request:
   - Title: "Add ComfyUI Plugin"
   - Description: Explain the plugin functionality
   - Include screenshots if possible

5. Wait for review and approval

## Step 5: Maintain Your Plugin

### Version Updates

When releasing new versions:

1. Update version in `manifest.yaml`
2. Update `__version__` in `__init__.py`
3. Commit changes
4. Create new GitHub release with updated tag

### Documentation

Keep these files updated:
- README.md - Installation and usage
- CHANGELOG.md - Version history
- examples/ - Sample workflows

## Best Practices

1. **Semantic Versioning**: Use MAJOR.MINOR.PATCH (e.g., 1.0.0)
2. **Changelog**: Document all changes
3. **Testing**: Test thoroughly before each release
4. **Security**: Never commit API keys or credentials
5. **License**: Include appropriate license (MIT recommended)

## Troubleshooting

### Installation Fails

- Check manifest.yaml syntax
- Verify all required files are present
- Ensure icon.svg is valid

### Plugin Not Working

- Check Dify logs for errors
- Verify ComfyUI URL is accessible
- Test credential validation

## Support

- GitHub Issues: For bug reports and feature requests
- Dify Community: For general questions
- Documentation: Keep README.md comprehensive
