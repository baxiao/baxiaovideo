import streamlit as st
import os
import json
import re
from openai import OpenAI

# --- 1. 安全配置 (Secrets 读取) ---
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error("❌ 未在 Secrets 中找到 DEEPSEEK_API_KEY，请检查配置。")
    st.stop()

# 初始化 DeepSeek 客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

st.set_page_config(page_title="短视频脚本策划专家", layout="wide")
st.title("📑 短视频全自动脚本策划器")
st.caption("专注文案生成、分镜描述与运镜脚本设计")

# --- 2. 核心逻辑函数 ---

def get_ai_script(topic, scene_count):
    """调用 DeepSeek 生成深度分镜脚本数据"""
    prompt = f"""
    针对主题“{topic}”，策划一个包含 {scene_count} 个镜头的短视频脚本。
    要求：
    1. 逻辑严密，适合拍摄或AI视频生成。
    2. 严格以 JSON 数组格式返回。
    3. 每个对象包含字段：
       - "scene_no": 序号 (居中展示),
       - "text": 旁白/文案内容,
       - "visual": 画面详细描述 (用于给AI绘图参考),
       - "camera": 运镜指令 (如: 缓慢推近, 环绕上升, 侧向平移).
    
    注意：只输出 JSON 数据，不要任何解释。
    """
    try:
        response = ds_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = response.choices[0].message.content
        
        # 强力清洗 JSON 杂质
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            return json.loads(raw_content.strip())
    except Exception as e:
        st.error(f"脚本生成失败: {e}")
        return None

# --- 3. 界面交互 ---

with st.sidebar:
    st.header("脚本参数设置")
    scene_num = st.slider("分镜镜头数量", min_value=1, max_value=10, value=4)
    st.info("💡 提示：暂停了图片和视频生成，专注文案创作。")

user_topic = st.text_input("请输入视频主题（关键词或短句）：", placeholder="例如：讲述一个关于孤独与勇气的科幻故事")

if st.button("🚀 开始策划脚本"):
    if not user_topic:
        st.warning("请先输入主题内容。")
    else:
        with st.spinner("DeepSeek 正在构思您的视频脚本..."):
            scenes = get_ai_script(user_topic, scene_num)
        
        if scenes:
            st.success(f"✅ 脚本生成完成，共计 {len(scenes)} 个镜头。")
            
            # 使用表格形式展示，方便一眼扫视
            for i, scene in enumerate(scenes):
                st.markdown(f"### --- 分镜 {scene.get('scene_no', i+1)} ---")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("**🎙️ 旁白文案 (点击下方可复制)**")
                    # 使用 text_area 方便用户全选复制
                    st.text_area("文案内容", value=scene['text'], height=100, key=f"text_{i}")
                    
                    st.markdown("**🎥 运镜脚本**")
                    st.code(scene['camera'], language="text")

                with col2:
                    st.markdown("**🖼️ 画面描述 (分镜镜头)**")
                    # 这里是原来的绘图描述，保留用于给用户参考
                    st.text_area("视觉参考描述", value=scene['visual'], height=150, key=f"vis_{i}")
            
            # 提供整体脚本下载
            full_script_text = ""
            for s in scenes:
                full_script_text += f"分镜{s.get('scene_no', '')}\n文案：{s['text']}\n画面：{s['visual']}\n运镜：{s['camera']}\n\n"
            
            st.download_button("📥 导出完整脚本 (TXT)", full_script_text, f"{user_topic}_脚本.txt")
            st.balloons()
