import streamlit as st
import os
import json
import re
import requests
from openai import OpenAI

# 尝试导入豆包 SDK
try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    st.error("❌ 缺少豆包依赖库。请在 requirements.txt 中添加 'volcengine-python-sdk-ark' 并重新部署。")
    st.stop()

# --- 1. 配置读取 ---
try:
    DS_KEY = st.secrets["DEEPSEEK_API_KEY"]
    AK = st.secrets["VOLC_ACCESS_KEY"]
    SK = st.secrets["VOLC_SECRET_KEY"]
    IMG_EP = st.secrets["DOUBAO_IMAGE_ENDPOINT"]
    # 视频生成目前部分为邀测，若无 endpoint 可先填空
    VID_EP = st.secrets.get("DOUBAO_VIDEO_ENDPOINT", "")
except Exception as e:
    st.error(f"Secrets 配置不全: {e}")
    st.stop()

# 初始化客户端
ds_client = OpenAI(api_key=DS_KEY, base_url="https://api.deepseek.com")
ark_client = Ark(ak=AK, sk=SK)

st.set_page_config(page_title="豆包智能视频工厂", layout="wide")
st.title("🎬 豆包 x DeepSeek 全自动视频工厂")

# --- 2. 核心函数 ---

def get_script(topic):
    """DeepSeek 策划脚本"""
    prompt = f"策划主题'{topic}'的短视频脚本，返回JSON数组，含text(文案), visual(画面描述), camera(运镜)。"
    res = ds_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":prompt}])
    match = re.search(r'\[.*\]', res.choices[0].message.content, re.DOTALL)
    return json.loads(match.group(0)) if match else None

def generate_doubao_img(prompt):
    """调用豆包绘图"""
    try:
        # 注意：不同模型的调用方法可能略有差异，请参考火山引擎最新文档
        response = ark_client.content_generation.create(
            model=IMG_EP,
            prompt=prompt,
        )
        # 获取生成的图片 URL
        return response.data[0].url
    except Exception as e:
        st.error(f"豆包绘图失败: {e}")
        return None

# --- 3. 界面逻辑 ---
topic = st.text_input("请输入视频主题：", "写实风格的赛博朋克城市")

if st.button("🚀 启动流水线"):
    with st.spinner("1. DeepSeek 正在生成脚本..."):
        scenes = get_script(topic)
    
    if scenes:
        for i, s in enumerate(scenes):
            st.divider()
            col1, col2, col3 = st.columns([1, 2, 2])
            
            with col1:
                st.info(f"**分镜 {i+1}**\n\n{s['text']}")
                st.caption(f"运镜: {s['camera']}")
                st.text_area(f"复制文案 {i+1}", s['text'], key=f"t{i}")

            img_url = None
            with col2:
                with st.spinner("豆包绘图中..."):
                    img_url = generate_doubao_img(s['visual'])
                    if img_url:
                        st.image(img_url)
                        st.download_button("下图片", requests.get(img_url).content, f"i_{i}.jpg", key=f"di{i}")

            with col3:
                st.warning("视频生成模块正在对接豆包视频 Endpoint...")
                # 待豆包视频 API 正式开通后，此处逻辑与绘图类似

        st.balloons()
