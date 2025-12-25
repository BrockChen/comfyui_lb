"""
Dify ComfyUI Plugin Entry Point
"""
from dify_plugin import DifyPluginEnv, plugin

# Initialize plugin environment
plugin_env = DifyPluginEnv()

# Start the plugin
if __name__ == '__main__':
    plugin.start()
