# Auto-ChatGPT

![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.43%2B-43B02A?style=flat&logo=selenium&logoColor=white)
![Chrome](https://img.shields.io/badge/Chrome-Automation-4285F4?style=flat&logo=googlechrome&logoColor=white)

**Auto-ChatGPT** 是一个基于 Selenium 的 ChatGPT 网页端自动化项目。项目将 ChatGPT 页面上的常见交互封装为可复用的 Python 操作能力，包括登录检测、新建对话、输入提示词、上传附件、发送消息、等待回复、读取回复、下载生成图片、重命名对话以及异常状态检测。

项目定位不是通用聊天机器人框架，也不是单一业务脚本，而是一个面向真实浏览器会话的 ChatGPT 自动操作层。上层脚本可以基于这些能力组合出批处理、内容生成、图像生成、附件处理等自动化流程。

## 功能 Features

- **浏览器会话**：使用独立 Chrome profile 启动 ChatGPT，支持保留登录态，避免污染日常浏览器环境。
- **登录状态检测**：自动识别当前账号是否已登录，并读取用户名和套餐信息。
- **人工登录衔接**：未登录时自动点击登录入口，并等待用户在真实浏览器窗口中完成登录。
- **对话管理**：支持创建新对话、判断新对话入口状态、重命名当前对话。
- **输入控制**：定位 ChatGPT 输入框，写入 prompt，并校验输入内容是否与预期一致。
- **附件上传**：通过页面文件输入控件上传本地附件，并等待附件进入 composer。
- **消息发送**：点击发送按钮，并确认用户消息已出现在当前对话中。
- **回复等待**：根据对话轮次和页面状态等待 assistant 回复完成。
- **内容读取**：读取最新 assistant 文本，也可读取页面正文用于异常检测。
- **图片保存**：从最新 assistant 回复中收集生成图片，并在浏览器上下文中读取 `blob:`、`data:image` 或后端资源后保存到本地。
- **异常检测**：识别请求过于频繁、图像生成限额、内容策略失败等状态。
- **结果记录**：将上层任务执行结果写入 JSON，支持断点续跑和失败排查。

## 具体流程

一次典型的 ChatGPT 自动操作流程如下：

```text
读取配置
  -> 启动 Chrome
  -> 打开 ChatGPT
  -> 检测登录状态
  -> 必要时等待人工登录
  -> 新建对话
  -> 定位输入框
  -> 可选：上传本地附件
  -> 等待附件上传完成
  -> 输入 prompt
  -> 校验 prompt
  -> 发送消息
  -> 等待用户消息出现
  -> 等待 assistant 回复完成
  -> 读取回复内容
  -> 可选：保存生成图片
  -> 可选：重命名对话
  -> 记录任务结果
```

当前示例入口 `examples/image_edit_script/main.py` 在上述基础能力之上实现了批处理逻辑，包括任务初始化、跳过已处理任务、保存生成结果、记录失败原因以及在触发限额时停止任务。

## 安装 Installation

项目要求 Python 3.13 或更高版本。

使用 `uv`：

```bash
uv sync
```

或使用 `pip`：

```bash
pip install -r requirements.txt
```

## 使用 Usage

当前示例脚本入口：

```bash
python examples/image_edit_script/main.py
```

首次运行时，程序会打开 Chrome 并访问 ChatGPT。如果当前 profile 尚未登录，程序会等待用户在浏览器中手动完成登录。

## 示例：批量 GPT 自动修图

`examples/image_edit_script/main.py` 提供了一个基于 ChatGPT 图像生成能力的批量自动修图示例。该示例会递归扫描本地图片目录，将图片逐张上传到 ChatGPT，发送固定修图 prompt，等待生成结果，并把生成图片保存到本地。

适用流程：

```text
扫描图片目录
  -> 生成待处理任务
  -> 跳过已完成任务
  -> 为当前图片新建对话
  -> 上传图片附件
  -> 输入固定修图 prompt
  -> 发送消息
  -> 等待 GPT 返回生成结果
  -> 下载生成图片
  -> 写入任务状态
  -> 继续处理下一张图片
```

运行方式：

```bash
python examples/image_edit_script/main.py
```

常用配置：

- `image_root_dir`：待批量处理的原图目录。
- `fixed_prompt`：用于修图的固定 prompt，例如保持人物身份和构图，只进行自然美化、肤色优化、背景处理等。
- `output.root_dir`：生成图片保存目录。
- `output.image_location`：生成图片保存位置，支持 `source` 或 `output`。
- `output.result_json_path`：批处理结果记录文件。
- `task.skip_policy_failed`：是否跳过此前被内容策略拒绝的任务。

脚本会记录每张图片的处理状态。再次运行时，已成功处理的图片会被跳过，适合在大量图片任务中断后继续执行。

## 配置 Configuration

主要配置文件位于 `config/config.json`。如果文件不存在，项目会根据 `utils/config.py` 中的默认配置自动生成。

常用配置项：

- `image_root_dir`：示例脚本中待上传附件的根目录。
- `fixed_prompt`：发送给 ChatGPT 的固定 prompt。
- `chrome.profile_dir`：Chrome 用户数据目录。
- `chrome.version_main`：本机 Chrome 主版本号。
- `chrome.driver_exe_path`：ChromeDriver 路径。
- `output.root_dir`：生成内容输出目录。
- `output.result_json_path`：结果记录 JSON 路径。
- `output.image_location`：输出位置，支持 `source` 或 `output`。
- `task.skip_policy_failed`：是否跳过此前被策略拒绝的任务。
- `human_like_interaction`：各步骤之间的随机等待时间配置。

## 项目结构

```text
chatgpt_page/                 ChatGPT 页面操作封装
chatgpt_page/sidebar/         侧边栏与对话重命名相关操作
utils/                        配置、日志、Selenium 工具、延迟控制
examples/image_edit_script/   基于 ChatGPT 操作能力实现的批处理示例
tests/                        单元测试
tools/                        辅助工具脚本
config/                       本地配置与 Chrome profile
output/                       默认输出目录
```

## 注意事项

- 本项目自动化的是 ChatGPT 网页端，不是 OpenAI API。
- 页面结构变化可能导致选择器失效，需要维护 `chatgpt_page/` 下的定位逻辑。
- 请求频率、图像生成额度和内容策略由 ChatGPT 服务端控制，脚本只能检测并记录，不能绕过限制。
- 使用附件上传或图像生成相关能力时，应确保输入内容来源、授权和用途合规。
