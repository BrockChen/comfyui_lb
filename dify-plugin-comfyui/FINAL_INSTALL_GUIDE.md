# 完整安装指南 - 已解决所有问题

## 🎯 最终可用版本

经过多次修复，插件现在可以正常工作了！

## 📋 已修复的问题

### 问题 1: Manifest Schema 错误
**错误**: `Type' Error:Field validation for 'Type' failed`

**原因**: Dify v0.5.1 需要完整的 manifest schema

**解决**: 
- 将 `type` 从 `tool` 改为 `plugin`
- 添加 `resource`, `meta`, `plugins` 部分
- 设置 `storage.size >= 1024`

### 问题 2: Author 字段无效
**错误**: `plugin_unique_identifier is not valid: Your Name/comfyui`

**原因**: author 不能包含空格

**解决**: 将 `Your Name` 改为 `comfyui-plugin`

### 问题 3: 签名验证失败
**错误**: `plugin has a bad signature`

**原因**: 本地打包的插件没有官方签名

**解决**: 使用 GitHub 安装或禁用验证

### 问题 4: 插件解析失败
**错误**: `Failed to parse response from plugin daemon`

**原因**: 导入语句不正确

**解决**: 修正 `ToolProviderCredentialValidationError` 的导入路径

## ✅ 当前配置（已验证可用）

### manifest.yaml
```yaml
version: 0.0.1
type: plugin
author: comfyui-plugin
name: comfyui
description:
  en_US: ComfyUI integration plugin for Dify
  zh_Hans: Dify 的 ComfyUI 集成插件
icon: icon.svg
label:
  en_US: ComfyUI
  zh_Hans: ComfyUI
created_at: 2025-12-21T00:00:00Z

resource:
  memory: 512
  permission:
    tool:
      enabled: true
    model:
      enabled: false
    endpoint:
      enabled: false
    app:
      enabled: false
    storage:
      enabled: true
      size: 1024

plugins:
  tools:
    - provider/comfyui.yaml

meta:
  version: 0.0.1
  arch:
    - amd64
    - arm64
  runner:
    language: python
    version: "3.12"
    entrypoint: main
```

### provider/comfyui.py (关键修复)
```python
from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
# ✅ 正确的导入路径
```

## 🚀 安装方法

### 方法 1: GitHub 安装（推荐）

#### 步骤 1: 推送到 GitHub
```bash
cd dify-plugin-comfyui

# 初始化（如果还没有）
git init
git add .
git commit -m "feat: ComfyUI plugin for Dify - production ready"

# 推送到 GitHub
git remote add origin https://github.com/YOUR_USERNAME/dify-plugin-comfyui.git
git branch -M main
git push -u origin main
```

#### 步骤 2: 创建 Release
1. 访问 GitHub 仓库
2. Releases → Create new release
3. Tag: `v0.0.1`
4. Title: `v0.0.1 - Initial Release`
5. Publish

#### 步骤 3: 在 Dify 安装
1. Dify → Settings → Plugins
2. Install from GitHub
3. 输入: `https://github.com/YOUR_USERNAME/dify-plugin-comfyui`
4. Install

✅ **成功！** 插件已安装并通过验证

### 方法 2: 本地安装（需禁用验证）

#### 步骤 1: 禁用签名验证

编辑 Dify 的 `.env` 文件：
```bash
PLUGIN_VERIFICATION_ENABLED=false
```

重启 Dify:
```bash
docker-compose down
docker-compose up -d
```

#### 步骤 2: 上传插件包

1. 确保已打包最新版本:
   ```bash
   cd /Users/aa01035/work/mcode/comfyui_lb
   rm -f dify-plugin-comfyui.difypkg
   dify plugin package dify-plugin-comfyui
   ```

2. 在 Dify 中上传 `dify-plugin-comfyui.difypkg`

✅ **成功！** 插件已安装

## ⚙️ 配置插件

安装后需要配置 ComfyUI 连接：

1. Settings → Plugins → ComfyUI → Settings
2. 填写 **ComfyUI Base URL**:
   - 本地: `http://localhost:8188`
   - 远程: `http://your-server:8188`
   - 负载均衡器: `http://your-lb:8100`
3. Test Connection
4. Save

## 🧪 测试插件

### 测试 1: 在 Workflow 中使用

创建工作流:
```
Code 节点 → ComfyUI 工具 → End 节点
```

Code 节点内容:
```python
import json

workflow = {
    # 使用 examples/basic_workflow.json 中的内容
}

return {"result": json.dumps(workflow)}
```

### 测试 2: 在 Agent 中使用

创建 Agent，添加 ComfyUI 工具，然后测试:
```
用户: 生成一张山景图片
Agent: (调用 ComfyUI 生成图片)
```

## 📦 文件清单

```
dify-plugin-comfyui/
├── manifest.yaml          ✅ 已修复所有字段
├── provider/
│   ├── comfyui.yaml      ✅ author 已更新
│   └── comfyui.py        ✅ 导入已修复
├── tools/
│   ├── generate_image.yaml ✅ author 已更新
│   └── generate_image.py   ✅ 实现完整
├── _assets/
│   └── icon.svg          ✅ 图标正常
├── main.py               ✅ 入口点正确
└── requirements.txt      ✅ 依赖完整
```

## 🔍 验证检查清单

打包前检查:
- [x] manifest.yaml 格式正确
- [x] type = plugin
- [x] author 无空格
- [x] resource.storage.size >= 1024
- [x] meta 部分完整
- [x] plugins 部分正确
- [x] 导入语句正确
- [x] icon.svg 存在

打包命令:
```bash
dify plugin package dify-plugin-comfyui
```

期望输出:
```
[INFO]plugin packaged successfully, output path: dify-plugin-comfyui.difypkg
```

## 🎉 成功标志

安装成功后，您应该能看到:

1. ✅ 插件出现在已安装列表
2. ✅ 状态显示为 "Active"
3. ✅ 可以在工具列表中找到 "ComfyUI"
4. ✅ 配置页面可以正常打开
5. ✅ 测试连接成功

## 🐛 如果仍有问题

### 检查 Dify 日志
```bash
docker logs dify-api -f
```

### 检查插件包内容
```bash
unzip -l dify-plugin-comfyui.difypkg
```

### 验证配置文件
```bash
cd dify-plugin-comfyui
python3 validate.py
```

## 📚 相关文档

- `TROUBLESHOOTING.md` - 打包问题解决
- `SIGNATURE_ISSUE.md` - 签名验证问题
- `AUTHOR_FIX.md` - Author 字段问题
- `SETUP_GUIDE.md` - 详细安装指南
- `QUICKSTART.md` - 快速开始

## 🎯 下一步

插件安装成功后:

1. ✅ 配置 ComfyUI 连接
2. ✅ 测试基本功能
3. ✅ 在实际工作流中使用
4. ✅ 根据需要调整参数
5. ✅ 分享给团队成员

---

**插件状态**: ✅ 生产就绪

**最后更新**: 2025-12-21

**版本**: v0.0.1
