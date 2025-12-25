"""
ComfyUI Image Generation Tool for Dify
"""
import json
import asyncio
import httpx
import uuid
from typing import Any
from collections.abc import Generator
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class GenerateImageTool(Tool):
    """
    Tool for generating images using ComfyUI workflow API
    """
    
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Invoke the ComfyUI image generation tool
        
        Args:
            tool_parameters: Tool parameters containing workflow_api
            
        Yields:
            ToolInvokeMessage: Progress updates and final result
        """
        # Get ComfyUI base URL from credentials
        base_url = self.runtime.credentials.get('comfyui_base_url', '').rstrip('/')
        if not base_url:
            yield self.create_text_message("Error: ComfyUI base URL not configured")
            return
        
        # Get workflow API from parameters
        workflow_api_str = tool_parameters.get('workflow_api', '')
        if not workflow_api_str:
            yield self.create_text_message("Error: workflow_api parameter is required")
            return
        
        # Parse workflow API JSON
        try:
            workflow_api = json.loads(workflow_api_str)
        except json.JSONDecodeError as e:
            yield self.create_text_message(f"Error: Invalid JSON in workflow_api: {str(e)}")
            return
        
        # Generate unique client ID
        client_id = f"dify_{uuid.uuid4().hex[:16]}"
        
        # Run async generation
        try:
            result = asyncio.run(self._generate_image(base_url, workflow_api, client_id))
            
            if result.get('success'):
                # Return the generated image
                image_data = result.get('image_data')
                filename = result.get('filename', 'generated_image.png')
                
                yield self.create_blob_message(
                    blob=image_data,
                    meta={'mime_type': 'image/png'},
                    save_as=filename
                )
                yield self.create_text_message(f"Successfully generated image: {filename}")
            else:
                error_msg = result.get('error', 'Unknown error')
                yield self.create_text_message(f"Error: {error_msg}")
                
        except Exception as e:
            yield self.create_text_message(f"Error during image generation: {str(e)}")
    
    async def _generate_image(self, base_url: str, workflow_api: dict, client_id: str) -> dict:
        """
        Async function to generate image using ComfyUI
        
        Args:
            base_url: ComfyUI base URL
            workflow_api: Workflow API JSON
            client_id: Unique client ID
            
        Returns:
            dict: Result containing success status, image data, or error message
        """
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Submit prompt
                payload = {
                    "prompt": workflow_api,
                    "client_id": client_id
                }
                
                response = await client.post(f"{base_url}/prompt", json=payload)
                response.raise_for_status()
                result = response.json()
                prompt_id = result.get('prompt_id')
                
                if not prompt_id:
                    return {'success': False, 'error': 'No prompt_id returned from ComfyUI'}
                
                # Wait for completion by polling history
                max_attempts = 150  # 5 minutes with 2s interval
                for _ in range(max_attempts):
                    await asyncio.sleep(2)
                    
                    # Check history
                    history_response = await client.get(f"{base_url}/history/{prompt_id}")
                    history_response.raise_for_status()
                    history = history_response.json()
                    
                    if prompt_id in history:
                        task_info = history[prompt_id]
                        status = task_info.get('status', {})
                        
                        if status.get('completed'):
                            # Extract image information
                            outputs = task_info.get('outputs', {})
                            image_info = None
                            
                            for node_id, node_output in outputs.items():
                                if 'images' in node_output:
                                    image_info = node_output['images'][0]
                                    break
                            
                            if not image_info:
                                return {'success': False, 'error': 'No images found in output'}
                            
                            # Download image
                            filename = image_info.get('filename')
                            subfolder = image_info.get('subfolder', '')
                            image_type = image_info.get('type', 'output')
                            
                            # Get backend name if using load balancer
                            backend_name = None
                            try:
                                task_response = await client.get(f"{base_url}/lb/tasks/{prompt_id}")
                                if task_response.status_code == 200:
                                    task_data = task_response.json()
                                    backend_name = task_data.get('backend_name')
                            except:
                                pass  # Not using load balancer
                            
                            # Download image
                            params = {
                                'filename': filename,
                                'subfolder': subfolder,
                                'type': image_type
                            }
                            if backend_name:
                                params['backend'] = backend_name
                            
                            image_response = await client.get(f"{base_url}/view", params=params)
                            image_response.raise_for_status()
                            
                            return {
                                'success': True,
                                'image_data': image_response.content,
                                'filename': filename
                            }
                
                return {'success': False, 'error': 'Timeout waiting for image generation'}
                
            except httpx.HTTPError as e:
                return {'success': False, 'error': f'HTTP error: {str(e)}'}
            except Exception as e:
                return {'success': False, 'error': f'Unexpected error: {str(e)}'}
