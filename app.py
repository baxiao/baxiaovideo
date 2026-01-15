import streamlit as st
import os
import json
import re
from openai import OpenAI
from volcenginesdkarkruntime import Ark

# --- 1. 初始化客户端 ---
try:
    # DeepSeek 客户端
    ds_client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    
    # 豆包/火山引擎客户端 (使用 Ark SDK)
    # 需安装: pip install volcengine-python-sdk-ark
    ark_client = Ark(
        ak=st.secrets["VOLC_ACCESS_KEY"],
        sk=st.secrets["VOLC_SECRET_KEY"]
    )
except Exception as e:
    st.error(f"配置加载失败，请检查 Secrets: {e}")
    st.stop()

st.set_page_config(page_title="豆包视频工厂", layout="wide")
st.title("🎬 豆包 x DeepSeek 全自动视频工厂")

# --- 2. 核心执行逻辑 ---

def get_script(topic):
    """DeepSeek 负责脚本大脑"""
    prompt = f"策划主题为'{topic}'的短视频脚本，返回JSON数组，含text(文案), visual(画面描述), camera(英文运镜指令)。"
    res = ds_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":prompt}])
    match = re.search(r'\[.*\]', res.choices[0].message.content, re.DOTALL)
    return json.loads(match.group(0)) if match else None

def generate_doubao_image(prompt):
    """调用豆包图像生成模型 (CV)"""
    try:
        # 调用火山引擎图像生成大模型
        response = ark_client.content_generation.create(
            model=st.secrets["DOUBAO_IMAGE_ENDPOINT"],
            prompt=prompt,
            style="cinematic", # 设置为电影感风格
            size="1280x720"
        )
        # 获取图片 URL 或 Base64
        return response.data[0].url
    except Exception as e:
        st.error(f"豆包绘图失败: {e}")
        return None

def generate_doubao_video(image_url, camera_move):
    """调用豆包视频生成模型 (Video Generation)"""
    try:
        response = ark_client.video_generation.create(
            model=st.secrets["DOUBAO_VIDEO_ENDPOINT"],
            image_url=image_url, # 豆包支持图生视频
            prompt=f"Cinematic motion: {camera_move}, high quality, realistic.",
        )
        # 视频生成通常是异步的，此处简化展示逻辑
        return response.data[0].url
    except Exception as e:
        st.warning(f"豆包视频生成暂不可用: {e}")
        return None

# --- 3. 界面交互 ---

user_topic = st.text_input("请输入视频主题：", "中国风水墨山水")

if st.button("🚀 启动豆包生产线"):
    if user_topic:
        with st.spinner("1. DeepSeek 正在构思脚本..."):
            scenes = get_script(user_topic)
        
        if scenes:
            for i, s in enumerate(scenes):
                st.divider()
                st.subheader(f"分镜 #{i+1}")
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    st.info(f"**文案:**\n{s['text']}")
                    st.caption(f"运镜: {s['camera']}")
                    st.text_area(f"复制文案 {i+1}", s['text'], height=70, key=f"t{i}")

                img_url = None
                with col2:
                    with st.spinner("豆包绘图中..."):
                        img_url = generate_doubao_image(s['visual'])
                        if img_url:
                            st.image(img_url, caption="豆包生成分镜图")
                            st.download_button("下载图片", requests.get(img_url).content, f"i_{i}.jpg", key=f"di{i}")

                with col3:
                    if img_url:
                        with st.spinner("豆包视频合成中..."):
                            video_url = generate_doubao_video(img_url, s['camera'])
                            if video_url:
                                st.video(video_url)
                                st.download_button("下载视频", requests.get(video_url).content, f"v_{i}.mp4", key=f"dv{i}")
            st.balloons()
