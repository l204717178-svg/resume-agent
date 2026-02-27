import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv

# 加载环境变量，强制使用 .env 里的值覆盖终端缓存
load_dotenv(override=True)

from resume_agent import process_resume_ui

# 设置 Streamlit 页面配置
st.set_page_config(
    page_title="超级简历 Agent V2.0",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------- 侧边栏配置 -----------------
with st.sidebar:
    st.title("⚙️ Agent 配置")
    st.markdown("请配置您的 DeepSeek 大模型大脑参数，以便开始诊断。")
    
    # API Key 输入框
    default_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    api_key_input = st.text_input(
        "DeepSeek API Key", 
        value=default_api_key, 
        type="password",
        help="我们将优先使用此处的 Key 进行调用"
    )
    
    # 目标公司偏好
    company_options = ["大厂", "创业公司", "外企", "传统企业"]
    company_type = st.selectbox(
        "投递目标公司类型", 
        options=company_options, 
        index=0,
        help="Agent 会根据您的选择调整最终简历的侧重点与行文调性"
    )

    st.markdown("---")
    st.markdown("💡 **关于此工具**\n\n基于 DeepSeek 强推理能力构建。运用双重筛选逆向思维，使用 STAR 法则为您一键重塑专业简历。")

# ----------------- 主界面 -----------------
st.title("🚀 超级简历 Agent V2.0")
st.markdown("上传您的历史简历，并粘贴目标岗位 JD，AI 将为您无情诊断并重构出一份**极致匹配**的单页 Markdown 简历。")

# 输入区域 (2 列布局)
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. 📄 上传原始简历")
    uploaded_file = st.file_uploader("支持 .txt 或 .pdf 格式", type=["txt", "pdf"])

with col2:
    st.subheader("2. 🎯 粘贴目标岗位 JD")
    jd_text_input = st.text_area("请将招聘软件上的职位描述粘贴在此处：", height=200, placeholder="例如：急招高级后端研发工程师...\n职位描述：\n1. 负责核心交易链路...\n职位要求：...")

# 居布执行按钮
st.markdown("<br>", unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    start_btn = st.button("✨ 开始残酷诊断与深度优化", use_container_width=True, type="primary")

# ----------------- 执行流转逻辑 -----------------
if start_btn:
    if not api_key_input:
        st.error("❌ 请在左侧配置您的 DeepSeek API Key！")
        st.stop()
    if not uploaded_file:
        st.error("❌ 请先上传一份您的原始简历文件！")
        st.stop()
    if not jd_text_input.strip():
        st.error("❌ 目标岗位的 JD 不能为空！")
        st.stop()

    # 读取上传文件的内容
    try:
        if uploaded_file.name.endswith('.pdf'):
            import fitz
            resume_text = ""
            # 将上传的文件保存到临时文件再让 fitz 读
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            with fitz.open(tmp_path) as doc:
                for page in doc:
                    resume_text += page.get_text() + "\n"
            os.remove(tmp_path)  # 清理临时文件
        else:
            resume_text = uploaded_file.getvalue().decode("utf-8")
    except Exception as e:
        st.error(f"读取简历文件失败: {e}")
        st.stop()

    st.markdown("---")
    
    # 建立进度展示区块
    with st.spinner("🤖 正在让 Agent 研读 JD 并透视您的简历经历..."):
        # 调用改写后的核心流程
        result = process_resume_ui(
            resume_text=resume_text,
            jd_text=jd_text_input,
            company_type=company_type,
            api_key=api_key_input
        )

    if result.get("status") == "error":
        st.error(result.get("error_msg"))
        st.stop()

    node1 = result["node1"]
    rewritten_exp = result["node2_rewritten"]
    final_resume = result["node3_final"]

    # ----------------- 结果呈现区 -----------------
    st.success("✅ **绝地反击！诊断与重塑成功！** 请查阅下方终局报告👇")
    
    st.markdown("### 🔍 [内部节点 1] 残酷诊断报告")
    
    # 核心指标卡片
    m_col1, m_col2 = st.columns([1, 2])
    with m_col1:
        st.metric(
            label="🎯 简历初始匹配度得分", 
            value=f"{node1.diagnosis.score} / 100", 
            delta="- 需要大修" if int(node1.diagnosis.score) < 80 else "底子不错"
        )
        st.caption(f"**🏅 竞争力真实评估**：\n\n{node1.diagnosis.competitiveness_analysis}")
        
    with m_col2:
        st.info(f"**🕵️ 侦测到的隐藏软性需求：**\n\n{node1.hidden_needs}")

    # 致命硬伤警告
    st.error("🧨 **致命劣势 (Fatal Flaws) 警告**：\n\n" + "\n".join([f"- {flaw}" for flaw in node1.diagnosis.fatal_flaws]))
    
    # 面试预警预测
    st.warning("🎯 **面试官犀利考点预测 (请提前准备)：**\n\n" + "\n".join([f"🤔 {q}" for q in node1.interview_prediction]))
    
    # 优化策略提示框
    st.success(f"💡 **建议抢救优化策略**： {node1.diagnosis.optimization_strategy}")
    
    st.markdown(f"**🔑 核心 ATS 通关密钥**： \n`{', '.join(node1.ats_keywords)}`")
    
    st.divider()
    
    st.markdown("#### ✍️ [节点 2] 经历极致浓缩骨架")
    st.caption("🤖 *去除了形容词水分，纯正 STAR 法则提取。如果仍有 `[]` 括号，请您填补这些缺失的量化数据。*")
    with st.expander("点击展开 / 收起重写的简历骨架", expanded=False):
        st.text_area("重写经历预览 (只读)", value=rewritten_exp, height=300, disabled=True, label_visibility="collapsed")
        
    st.divider()

    st.markdown(f"### 🏭 [节点 3] 最终一页纸简历 ({company_type} 定向排版)")
    st.caption("✨ *吸纳了目标岗位的灵魂和隐藏通关秘诀，直接复用这份精美的 Markdown 文本。*")
    
    # 使用代码块包裹或选项卡渲染
    tab_render, tab_raw = st.tabs(["👀 渲染预览模式", "📝 Markdown 源码模式"])
    
    with tab_render:
        with st.container(border=True):
            st.markdown(final_resume)
            
    with tab_raw:
        st.code(final_resume, language="markdown")

    st.markdown("<br>", unsafe_allow_html=True)
    # 下载按钮
    st.download_button(
        label="⬇️ 一键下载 .md 终版简历",
        data=final_resume.encode("utf-8"),
        file_name=f"超级简历_{company_type}版.md",
        mime="text/markdown",
        type="primary",
        use_container_width=True
    )
