import os
import argparse
import json
from pydantic import BaseModel, Field
from openai import OpenAI

# ---------------------------------------------------------
# Pydantic 结构定义 (用于节点 1 强制 JSON 输出)
# ---------------------------------------------------------
class DiagnosisResult(BaseModel):
    score: int = Field(description="整体匹配度评分 (0-100)")
    fatal_flaws: list[str] = Field(description="列出 3 个若不修改将直接导致被刷的硬伤（缺失的关键要素或逻辑断层）")
    optimization_strategy: str = Field(description="指明经历中哪些被忽视的细节可以用来弥补这些劣势")

class Node1Output(BaseModel):
    core_responsibilities: list[str] = Field(description="提取核心职责 (3-5条)")
    hard_skills: list[str] = Field(description="必备硬技能")
    ats_keywords: list[str] = Field(description="ATS 高频关键词清单")
    hidden_needs: str = Field(description="隐藏需求（业务痛点、团队协作风格）")
    diagnosis: DiagnosisResult

# ---------------------------------------------------------
# 文件解析模块 (支持 TXT 和 PDF)
# ---------------------------------------------------------
def read_file_content(filepath: str) -> str:
    """自动判断文件类型并提取纯文本内容。支持 .txt 和 .pdf"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        try:
            import fitz  # PyMuPDF
            text = ""
            with fitz.open(filepath) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
            return text
        except ImportError:
            raise ImportError(f"无法读取 {filepath}。请先安装依赖: pip install pymupdf")
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

# ---------------------------------------------------------
# Resume Agent 核心类 (DeepSeek 版)
# ---------------------------------------------------------
class ResumeAgent:
    def __init__(self, model_name="deepseek-chat", api_key=None):
        """
        初始化 OpenAI 客户端，配合 DeepSeek API。
        如果不传入 api_key，首先尝试聪明的读取当前目录下的 .env 文件。
        如果仍然没有，sdk 会自动尝试读取 DEEPSEEK_API_KEY 或者 OPENAI_API_KEY 环境变量。
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        api_key = (api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("未提供 API Key。请设置 DEEPSEEK_API_KEY 环境变量或直接传入。")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"  # DeepSeek API 的基础地址
        )
        self.model_name = model_name
        
        # 赋予 Agent 顶级招聘专家 Persona
        self.system_instruction = (
            "你是一个以结果为导向的顶级招聘专家、岗位分析师和 ATS (自动追踪系统) 算法模拟器。\n"
            "你的首要目标是：最大化用户简历通过双重筛选（ATS 关键词匹配 + 挑剔的人工 HR 面试）的概率。\n\n"
            "【强制规则】\n"
            "1. 绝对禁止捏造、虚构、夸大任何用户经历。\n"
            "2. 绝对禁止使用奉承、安慰、附和或情绪化语言。\n"
            "3. 事实、逻辑、数据优先。所有输出必须清晰、具体、可执行。\n"
            "4. 深刻理解不同体量公司（大厂 vs 创业公司）的筛选偏好。"
        )

    def analyze_jd_and_match(self, resume_text: str, jd_text: str) -> Node1Output:
        """
        Node 1：深度解析 JD 与核心匹配度诊断
        输入: 完整经历, 目标 JD
        输出: 结构化的 JSON 对象
        """
        prompt = (
            f"目标 JD:\n{jd_text}\n\n"
            f"完整经历:\n{resume_text}\n\n"
            "任务：\n"
            "1. 透视目标 JD：提取核心职责 (3-5条)、必备硬技能、梳理 ATS 高频关键词清单、洞察隐藏需求（业务痛点、团队协作风格）。\n"
            "2. 残酷诊断：对比用户的 [完整经历] 与该 JD，进行初步匹配。输出整体匹配度评分 (0-100)，列出列出 3 个致命劣势，并提供优化策略（指明经历中哪些被忽视的细节可以用来弥补这些劣势）。\n"
            "请以冷酷、精炼的方式输出，不带任何废话。\n"
            "你必须严格返回一个 JSON 对象，结构必须完全符合以下定义，不要包裹在 Markdown 代码块里，直接返回 JSON 字符串本身：\n"
            "{\n"
            '  "core_responsibilities": ["职责1", "职责2"],\n'
            '  "hard_skills": ["技能1"],\n'
            '  "ats_keywords": ["关键词1"],\n'
            '  "hidden_needs": "隐藏需求描述",\n'
            '  "diagnosis": {\n'
            '    "score": 85,\n'
            '    "fatal_flaws": ["硬伤1", "硬伤2", "硬伤3"],\n'
            '    "optimization_strategy": "优化策略描述"\n'
            "  }\n"
            "}"
        )
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2, # 保持客观冷酷的分析风格
        )
        
        json_text = response.choices[0].message.content
        # 将模型返回的 JSON 解析为 Python 对象
        return Node1Output.model_validate_json(json_text)

    def rewrite_experience(self, resume_text: str, ats_keywords: list[str]) -> str:
        """
        Node 2：STAR 骨架重塑 (经历提取和重写)
        输入: 完整经历, Node1 提取的 ATS 关键词
        输出: 重写后的文本
        """
        prompt = (
            f"完整经历:\n{resume_text}\n\n"
            f"ATS 关键词:\n{', '.join(ats_keywords)}\n\n"
            "任务：\n"
            "作为简历优化专家，提取上述用户经历中与这批 ATS 关键词匹配度最高的部分，并严格使用 STAR 法则 (情境-任务-行动-结果) 进行重写。\n\n"
            "【重写红线】\n"
            "1. S (情境) & T (任务)：一句话带过，体现业务复杂度和目标。\n"
            "2. A (行动)：必须包含具体的工具、方法论和上述的 ATS 关键词，自然融入，拒绝生硬堆砌。\n"
            "3. R (结果)：强制要求量化！没有明确数字的，必须在括号内标注 [此处需用户补充具体数据/产出指标]。\n"
            "4. 每段经历控制在 80-120 字，拒绝空泛的形容词（如“极大地提升了”、“负责了全面的”）。\n\n"
            "只输出重写后的经历文本，不要带任何寒暄和解释性文本。"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()

    def generate_final_resume(self, rewritten_experience: str, hidden_needs: str, company_type: str) -> str:
        """
        Node 3：终局生成与定向分发 (最终 Markdown 简历)
        输入: 被重写的经历 (Node2), JD隐藏需求 (Node1), 公司类型 (用户设定)
        输出: 最终排版文本
        """
        prompt = (
            f"重写的经历片段:\n{rewritten_experience}\n\n"
            f"JD 中分析出的隐藏需求:\n{hidden_needs}\n\n"
            f"当前投递公司的类型:\n{company_type}\n\n"
            "任务：\n"
            "基于前面的所有分析和重写结果，生成一份结构完美、高度定制化的最终版一页纸简历文本。\n\n"
            "【定制化偏好要求】\n"
            "若为【大厂】：极度强化数据驱动、规模化业务场景、系统性思维与方法论沉淀。\n"
            "若为【创业公司】：强化从 0 到 1 的搭建经验、多面手能力（闭环跑通）和快速迭代能力。\n"
            "若为【外企】或【传统企业】：请根据你的专业直觉，调整强调重点为流程合规、持续集成或跨团队沟通。\n\n"
            "【简历必须包含的标准模块】\n"
            "- 头部信息（需预留姓名/联系方式占位符，如 [填写姓名]）\n"
            "- 专业技能（硬技能优先，分点排列，请融入那些 ATS 关键词）\n"
            "- 工作/实习经历（融入重写后的经历片段，保持 STAR 法则的犀利）\n"
            "- 项目经历\n"
            "- 教育背景\n\n"
            "输出要求：\n"
            "只输出最终的 Markdown 排版文本，不要输出任何额外的解释性话语。"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        text = response.choices[0].message.content.strip()
        
        # 去除大语言模型可能自动添加的 ```markdown 标记
        if text.startswith("```markdown"):
            text = text[len("```markdown"):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        return text

# ---------------------------------------------------------
# 主干流转管道 (Pipeline)
# ---------------------------------------------------------
def process_resume(resume_filepath: str, jd_filepath: str, company_type: str, output_filepath: str, api_key: str = None) -> None:
    print("🚀 初始化超级简历 Agent (DeepSeek 版)...")
    try:
        agent = ResumeAgent(api_key=api_key)
    except Exception as e:
        print(f"❌ 初始化失败，请确保您设置了 DEEPSEEK_API_KEY 环境变量，或者网络通行正常。错误详情: {e}")
        return

    # 1. 文本读取
    if not os.path.exists(resume_filepath):
        print(f"❌ 找不到简历文件: {resume_filepath}")
        return
    if not os.path.exists(jd_filepath):
        print(f"❌ 找不到 JD 文件: {jd_filepath}")
        return

    print("📄 正在读取你的原始简历和目标 JD...")
    try:
        resume_text = read_file_content(resume_filepath)
        jd_text = read_file_content(jd_filepath)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    # 2. 调用 Node 1
    print("\n🔍 [节点 1] 正在透视分析 JD 并为您诊断初始匹配度...")
    node1_out = agent.analyze_jd_and_match(resume_text, jd_text)
    
    print("\n================ [残酷诊断报告] ================")
    print(f"⚠️  整体匹配度评分: {node1_out.diagnosis.score}/100")
    print("🧨 致命劣势 (Fatal Flaws):")
    for idx, flaw in enumerate(node1_out.diagnosis.fatal_flaws, 1):
        print(f"   {idx}. {flaw}")
    print(f"💡 优化策略: {node1_out.diagnosis.optimization_strategy}")
    print("\n🔑 提取到的 ATS 高频关键词: ", ", ".join(node1_out.ats_keywords))
    print(f"🕵️  洞察到的隐藏需求: {node1_out.hidden_needs}")
    print("================================================")
    
    # 3. 调用 Node 2
    print("\n✍️  [节点 2] 正在运用 STAR 骨架重塑核心经历...")
    rewritten_exp = agent.rewrite_experience(resume_text, node1_out.ats_keywords)
    print("\n==== [经历重写预览 (截取前面部分)] ====")
    preview_lines = rewritten_exp.split("\n")[:10]
    print("\n".join(preview_lines) + ("\n..." if len(preview_lines) >= 10 else ""))
    print("=======================================")
    
    # 4. 调用 Node 3
    print(f"\n🏭 [节点 3] 正在以此为基础生成最终版定向 ({company_type}) 排版简历...")
    final_resume = agent.generate_final_resume(rewritten_exp, node1_out.hidden_needs, company_type)
    
    # 保存结果
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(final_resume)
    
    print(f"\n✅ 终局生成完毕！定制简历已保存至: {output_filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="超级简历 Agent (DeepSeek 版)")
    parser.add_argument("--resume", type=str, default="我的真实简历.pdf", help="原始经历文件的路径")
    parser.add_argument("--jd", type=str, default="jd.txt", help="目标 JD (职位描述) 文件的路径")
    parser.add_argument("--company", type=str, default="大厂", help="目标公司类型 (如: 大厂/创业公司/外企)")
    parser.add_argument("--output", type=str, default="final_resume.md", help="最终生成的简历文件输出路径")
    
    args = parser.parse_args()
    
    # 为了演示目的，自动生成测试文件（如果文件不存在）
    if not os.path.exists(args.resume):
        with open(args.resume, "w", encoding="utf-8") as f:
            f.write("我是一个开发工程师，大概3年经验。之前在某公司做过后端接口开发，也搞过数据库表结构设计。能用 Python 爬虫抓点数据，偶尔也看看前端页面怎么写。有比较强的责任心。带过几个实习生。")
            
    if not os.path.exists(args.jd):
        with open(args.jd, "w", encoding="utf-8") as f:
            f.write("急招高级后端研发工程师。\n\n"
                    "职位描述：\n"
                    "1. 负责公司核心交易链路的高并发后端服务架构设计与开发；\n"
                    "2. 主导或参与微服务治理、性能调优和解耦优化；\n"
                    "3. 带领小团队，解决业务上的卡点。\n\n"
                    "职位要求：\n"
                    "1. 熟练掌握 C++/Go/Java/Python 中至少一门语言；\n"
                    "2. 精通 Redis、MySQL 等常用存储组件，有深度的 SQL 调优经验；\n"
                    "3. 具备优秀的系统分析和拆解能力。\n"
                    "加分项：之前有过互联网一线大厂高并发架构经验优先，抗压能力强。")

    process_resume(
        resume_filepath=args.resume,
        jd_filepath=args.jd,
        company_type=args.company,
        output_filepath=args.output
    )
