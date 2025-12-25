# 插件签名验证问题解决方案

## 错误信息
```
plugin verification has been enabled, and the plugin you want to install has a bad signature
```

## 原因
Dify 启用了插件签名验证，本地打包的 `.difypkg` 文件没有官方签名，因此无法直接安装。

## 解决方案

### 方案 1: 禁用签名验证（仅用于开发/测试）

如果您是自托管的 Dify 实例，可以临时禁用签名验证：

#### Docker 部署
编辑 `docker-compose.yml` 或环境变量文件，添加：

```yaml
services:
  api:
    environment:
      - PLUGIN_VERIFICATION_ENABLED=false
```

或在 `.env` 文件中：
```bash
PLUGIN_VERIFICATION_ENABLED=false
```

然后重启 Dify：
```bash
docker-compose down
docker-compose up -d
```

#### 源码部署
在 Dify 的配置文件中设置：
```python
PLUGIN_VERIFICATION_ENABLED = False
```

### 方案 2: 通过 GitHub 安装（推荐）

这是官方推荐的方式，不需要禁用签名验证：

#### 步骤 1: 推送到 GitHub

```bash
cd dify-plugin-comfyui

# 初始化 git（如果还没有）
git init

# 添加所有文件
git add .

# 提交
git commit -m "feat: ComfyUI plugin for Dify"

# 添加远程仓库（替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/dify-plugin-comfyui.git

# 推送
git branch -M main
git push -u origin main
```

#### 步骤 2: 创建 GitHub Release

1. 访问你的 GitHub 仓库
2. 点击 **Releases** → **Create a new release**
3. 填写信息：
   - Tag: `v0.0.1`
   - Title: `v0.0.1 - Initial Release`
   - Description: 简要说明
4. 点击 **Publish release**

#### 步骤 3: 在 Dify 中从 GitHub 安装

1. 打开 Dify → **Settings** → **Plugins**
2. 点击 **Install from GitHub**
3. 输入仓库 URL：
   ```
   https://github.com/YOUR_USERNAME/dify-plugin-comfyui
   ```
4. 点击 **Install**

✅ 从 GitHub 安装的插件会自动通过验证！

### 方案 3: 使用调试模式（开发专用）

如果您正在开发插件，可以使用调试模式：

#### 步骤 1: 获取调试凭据

1. 在 Dify 中进入 **Settings** → **Plugins** → **Debug**
2. 获取 **Debug Key** 和 **Remote Host**

#### 步骤 2: 配置环境

在插件目录创建 `.env` 文件：
```bash
INSTALL_METHOD=remote
INSTALL_KEY=your-debug-key-here
REMOTE_INSTALL_HOST=your-dify-host
REMOTE_INSTALL_PORT=5003
```

#### 步骤 3: 运行调试模式

```bash
cd dify-plugin-comfyui
pip install -r requirements.txt
python -m main
```

插件会自动安装到 Dify，无需签名验证。

## 推荐方案对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 禁用验证 | 自托管测试环境 | 简单快速 | 降低安全性 |
| GitHub 安装 | 生产环境 | 安全、官方推荐 | 需要 GitHub 账号 |
| 调试模式 | 插件开发 | 实时更新 | 仅限开发 |

## 最佳实践

### 开发阶段
使用**调试模式**进行开发和测试

### 测试阶段
使用**禁用验证**在测试环境快速验证

### 生产阶段
使用 **GitHub 安装**部署到生产环境

## 注意事项

⚠️ **安全警告**
- 不要在生产环境禁用签名验证
- 只安装来自可信来源的插件
- 定期更新插件到最新版本

## 快速开始（推荐）

如果您想立即测试插件功能，最快的方式是：

```bash
# 1. 推送到 GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/dify-plugin-comfyui.git
git push -u origin main

# 2. 创建 Release (通过 GitHub 网页)

# 3. 在 Dify 中从 GitHub 安装
# 输入: https://github.com/YOUR_USERNAME/dify-plugin-comfyui
```

✅ 完成！插件已安装并通过验证。

## 故障排除

### GitHub 安装失败
- 确保仓库是 public
- 检查是否创建了 Release
- 验证 manifest.yaml 格式正确

### 调试模式连接失败
- 检查 Debug Key 是否正确
- 确认 Dify 实例可访问
- 验证端口 5003 未被占用

### 签名验证仍然失败
- 确认环境变量已生效
- 重启 Dify 服务
- 检查 Dify 版本是否支持该配置
