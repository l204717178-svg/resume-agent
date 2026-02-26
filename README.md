# 超级简历 Agent V2.0 (DeepSeek 版)

这是一个可以本地自动化运行、针对性优化个人简历并通过双重筛选（ATS 关键词匹配 + HR 面试挑剔）的智能体工作流脚本。基于 DeepSeek 模型构建。

## 功能特性
1. **深度解析 JD 与核心诊断**: 接受 `jd.txt` 中的内容，使用结构化 JSON 给出现状致命缺陷，并提取 ATS 高频关键词与隐藏需求。
2. **STAR 骨架重塑**: 自动化使用 STAR 法则（情境-任务-行动-结果）修改您的原始简历，剔除废话，强制增加数据和业绩指标。
3. **支持 PDF / TXT 格式**: 直接支持读取原生 `.pdf` 简历文件。
4. **定向化生成排版**: 只要调整参数，就可以一秒切换成极具【大厂味】或【创业公司多面手味】的专属精简 Markdown 简历。

## 运行环境
- Python 3.9+
- 安装依赖库：
  ```bash
  pip install openai pydantic pymupdf python-dotenv
  ```

## 快速配置
1. 将自己的简历拖拽至根目录并命名为：`我的真实简历.pdf`。
2. 将招聘平台的职位描述复制到 `jd.txt` 中。
3. 打开 `.env` 文件（如果没有自行创建），配置好你的 DeepSeek API Key（请注意保密，绝对不要将该文件推送到公开的 Git 仓库！）：
   ```env
   DEEPSEEK_API_KEY="sk-xxxxxxxxxx"
   ```

## 运行指令
在终端中执行：
```bash
python resume_agent.py
```
这会自动抓取当前目录下的 `我的真实简历.pdf` 和 `jd.txt`，完成后将会在当前目录下为您输出排版清爽、语言犀利的终极版本：`final_resume.md`。
