import streamlit as st
import os
import json
import re
from openai import OpenAI
from google import genai
from google.genai import types

# --- 1. 配置与安全检查 ---
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
    GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("❌ 请在 Streamlit Secrets 中配置 DEEPSEEK_API_KEY 和 GOOGLE_API_KEY")
    st.stop()

# 初始化客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
google_client = genai.Client(api_key=GOOGLE_KEY)

st.set_page_config(page_title="视频工厂-最终版", layout="wide")
st.title("🎬 视频全自动生产流水线")

# --- 2. 核心逻辑 ---

def get_ai_script(topic):
    """DeepSeek 生成并清洗 JSON"""
    prompt = f"针对'{topic}'生成3个短视频分镜JSON，包含text(文案), visual(画面描述), camera(运镜)。只输出JSON。"
    response = ds_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":prompt}])
    raw = response.choices[0].message.content
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group(0)) if match else None

def generate_image_safe(desc):
    """尝试所有可能的图片模型名称"""
    for m in ['imagen-3.0-generate-001', 'imagen-3.0-fast-001', 'imagen-3.0-capability-001']:
        try:
            res = google_client.models.generate_images(model=m, prompt=desc, 
                                                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9"))
            return res.generated_images[0].image_bytes
        except: continue
    return None

def generate_video_safe(img_bytes, cam):
    """生成视频 (若无Veo权限则跳过)"""
    try:
        res = google_client.models.generate_content(model='veo-2.0', 
                                                 contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), f"Motion: {cam}"])
        return res.candidates[0].content.parts[0].inline_data.data
    except: return None

# --- 3. 运行界面 ---

topic = st.text_input("视频主题：", "写实风格的赛博朋克上海")

if st.button("🚀 开始生产"):
    with st.spinner("正在构思脚本..."):
        scenes = get_ai_script(topic)
    
    if scenes:
        for i, s in enumerate(scenes):
            st.divider()
            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                st.info(f"**分镜 {i+1}**\n\n{s['text']}")
                st.caption(f"运镜: {s['camera']}")
            
            img = None
            with c2:
                with st.spinner("绘图中..."):
                    img = generate_image_safe(s['visual'])
                    if img: 
                        st.image(img)
                        st.download_button("下图片", img, f"i_{i}.jpg", key=f"i{i}")
                    else: st.error("绘图模型不可用，请检查API权限")

            with c3:
                if img:
                    with st.spinner("渲染视频..."):
                        vid = generate_video_safe(img, s['camera'])
                        if vid: 
                            st.video(vid)
                            st.download_button("下视频", vid, f"v_{i}.mp4", key=f"v{i}")
                        else: st.warning("Veo视频模型暂无权限")

        st.balloons()
