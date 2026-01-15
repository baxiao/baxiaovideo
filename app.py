import streamlit as st
import os
import requests
import json
from openai import OpenAI

# --- 1. 初始化配置 (从 Secrets 读取) ---
DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]

# 初始化 DeepSeek 客户端
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

st.set_page_config(page_title="全自动视频工厂", layout="wide")
st.title("🎬 全自动视频生成工厂")

# --- 2. 核心功能函数 ---
def get_ai_script(topic):
    """根据主题生成结构化脚本"""
    prompt = f"""
    针对主题 '{topic}'，生成一个短视频脚本。
    必须严格返回 JSON 格式，不要包含任何多余文字。
    格式示例：
    [
      {{"scene": 1, "text": "文案内容", "visual": "画面详细描述", "camera": "运镜方式"}},
      ...
    ]
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    # 解析 JSON 结果
    return json.loads(response.choices[0].message.content)

# --- 3. 界面交互 ---
user_topic = st.text_input("请输入视频关键词或短句：", placeholder="例如：未来的深海基地")

if st.button("🚀 开始全自动化流水线生成"):
    if not user_topic:
        st.warning("请先输入内容")
    else:
        # 第一步：生成脚本
        with st.spinner("DeepSeek 正在解析分镜..."):
            scenes = get_ai_script(user_topic)
            st.success(f"✅ 已成功生成 {len(scenes)} 个分镜脚本")
            
        # 遍历每一个分镜进行处理
        for i, scene in enumerate(scenes):
            st.divider()
            st.subheader(f"分镜 #{i+1}")
            
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.info(f"📜 **文案**\n\n{scene['text']}")
                st.write(f"🎥 **运镜**: {scene['camera']}")
                # 文案可复制
                st.button(f"复制文案 #{i+1}", on_click=lambda t=scene['text']: st.write(f"已复制: {t}"), key=f"copy_{i}")

            with col2:
                with st.spinner(f"正在绘制分镜图 {i+1}..."):
                    # 模拟调用 Nano Banana (Imagen 3)
                    # 实际调用时请使用 Google genai 库
                    img_url = "https://picsum.photos/1280/720" # 占位图
                    st.image(img_url, caption=f"画面描述: {scene['visual']}")
                    
                    # 图片下载
                    img_data = requests.get(img_url).content
                    st.download_button("📥 下载图片", img_data, f"scene_{i+1}.jpg", "image/jpeg", key=f"dl_img_{i}")

            with col3:
                with st.spinner(f"正在生成运镜视频 {i+1}..."):
                    # 模拟调用 Veo (根据 img_url 和 scene['camera'] 生成视频)
                    video_url = "https://www.w3schools.com/html/mov_bbb.mp4" # 占位视频
                    st.video(video_url)
                    
                    # 视频下载
                    video_data = requests.get(video_url).content
                    st.download_button("📥 下载视频", video_data, f"video_{i+1}.mp4", "video/mp4", key=f"dl_vid_{i}")

        st.balloons()
