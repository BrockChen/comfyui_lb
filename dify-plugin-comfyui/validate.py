"""
Validation script for Dify ComfyUI Plugin
Run this to check if the plugin structure is correct
"""
import os
import yaml
import json
from pathlib import Path

def validate_plugin():
    """Validate plugin structure and configuration"""
    errors = []
    warnings = []
    
    # Check required files
    required_files = [
        'manifest.yaml',
        'provider/comfyui.yaml',
        'provider/comfyui.py',
        'tools/generate_image.yaml',
        'tools/generate_image.py',
        '_assets/icon.svg',
        'README.md',
        'LICENSE',
        'requirements.txt'
    ]
    
    print("Checking required files...")
    for file_path in required_files:
        if not os.path.exists(file_path):
            errors.append(f"Missing required file: {file_path}")
        else:
            print(f"✓ {file_path}")
    
    # Validate YAML files
    yaml_files = [
        'manifest.yaml',
        'provider/comfyui.yaml',
        'tools/generate_image.yaml'
    ]
    
    print("\nValidating YAML files...")
    for yaml_file in yaml_files:
        if os.path.exists(yaml_file):
            try:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
                print(f"✓ {yaml_file} is valid YAML")
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in {yaml_file}: {str(e)}")
    
    # Validate example JSON
    print("\nValidating example workflow...")
    example_json = 'examples/basic_workflow.json'
    if os.path.exists(example_json):
        try:
            with open(example_json, 'r') as f:
                json.load(f)
            print(f"✓ {example_json} is valid JSON")
        except json.JSONDecodeError as e:
            warnings.append(f"Invalid JSON in {example_json}: {str(e)}")
    
    # Check Python syntax
    print("\nChecking Python files...")
    python_files = [
        'provider/comfyui.py',
        'tools/generate_image.py',
        'main.py'
    ]
    
    for py_file in python_files:
        if os.path.exists(py_file):
            try:
                with open(py_file, 'r') as f:
                    compile(f.read(), py_file, 'exec')
                print(f"✓ {py_file} has valid syntax")
            except SyntaxError as e:
                errors.append(f"Syntax error in {py_file}: {str(e)}")
    
    # Print results
    print("\n" + "="*50)
    if errors:
        print("ERRORS FOUND:")
        for error in errors:
            print(f"  ❌ {error}")
    
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    
    if not errors and not warnings:
        print("✅ All validations passed!")
        print("\nNext steps:")
        print("1. Test the plugin with: python -m main")
        print("2. Package with: dify plugin package .")
        print("3. Publish to GitHub")
    elif not errors:
        print("\n✅ No critical errors found")
        print("⚠️  Please review warnings above")
    else:
        print("\n❌ Please fix errors before proceeding")
    
    print("="*50)
    
    return len(errors) == 0

if __name__ == '__main__':
    # Change to plugin directory
    plugin_dir = Path(__file__).parent
    os.chdir(plugin_dir)
    
    print("Validating Dify ComfyUI Plugin")
    print("="*50)
    
    success = validate_plugin()
    exit(0 if success else 1)
