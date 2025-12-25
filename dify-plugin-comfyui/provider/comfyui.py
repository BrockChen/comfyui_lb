"""
ComfyUI Provider for Dify
"""
from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class ComfyUIProvider(ToolProvider):
    """
    Provider for ComfyUI tools
    """
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate the provider credentials
        
        Args:
            credentials: Provider credentials containing comfyui_base_url
            
        Raises:
            ToolProviderCredentialValidationError: If credentials are invalid
        """
        import httpx
        
        base_url = credentials.get('comfyui_base_url', '').rstrip('/')
        
        if not base_url:
            raise ToolProviderCredentialValidationError('ComfyUI base URL is required')
        
        # Test connection to ComfyUI
        try:
            with httpx.Client(timeout=10.0) as client:
                # Try to get queue status as a health check
                response = client.get(f"{base_url}/queue")
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise ToolProviderCredentialValidationError(
                f'Failed to connect to ComfyUI at {base_url}: {str(e)}'
            )
        except Exception as e:
            raise ToolProviderCredentialValidationError(
                f'Unexpected error validating ComfyUI connection: {str(e)}'
            )
