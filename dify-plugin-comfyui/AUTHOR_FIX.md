# Author 字段修复说明

## 问题
安装插件时报错：
```
plugin_unique_identifier is not valid: Your Name/comfyui:0.0.1
```

## 原因
`author` 字段不能包含空格或特殊字符，"Your Name" 是无效的标识符。

## 解决方案
将所有配置文件中的 `author` 字段从 `Your Name` 改为 `comfyui-plugin`

### 修改的文件
1. `manifest.yaml` - 主配置
2. `provider/comfyui.yaml` - 提供商配置  
3. `tools/generate_image.yaml` - 工具配置

### 插件标识符格式
```
{author}/{name}:{version}@{hash}
```

修复后：
```
comfyui-plugin/comfyui:0.0.1@{hash}
```

## 重新打包
```bash
rm -f dify-plugin-comfyui.difypkg
dify plugin package dify-plugin-comfyui
```

✅ 现在可以正常安装了！
