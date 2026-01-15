import streamlit as st
import os
import json
import re
from openai import OpenAI
from google import genai
from google.genai import types

# --- 1. 配置读取 ---
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
    GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("❌ 请先在 Streamlit Secrets 中配置 DEEPSEEK_API_KEY 和 GOOGLE_API_KEY")
    st.stop()

# 初始化客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
google_client = genai.Client(api_key=GOOGLE_KEY)

st.set_page_config(page_title="视频工厂-自适应版", layout="wide")
st.title("🎬 视频全自动生产流水线")

# --- 2. 自动检测可用模型 ---
with st.sidebar:
    st.header("系统状态检查")
    try:
        # 获取用户账号下所有可用的模型列表
        all_models = [m.name for m in google_client.models.list()]
        img_models = [m for m in all_models if "imagen" in m.lower() or "image" in m.lower()]
        vid_models = [m for m in all_models if "veo" in m.lower()]
        
        st.success("✅ API 连接正常")
        st.write("**可用绘图模型:**", img_models if img_models else "未找到")
        st.write("**可用视频模型:**", vid_models if vid_models else "未找到")
        
        # 自动挑选最优先的绘图模型
        SELECTED_IMG_MODEL = img_models[0] if img_models else 'imagen-3.0-generate-001'
        # 自动挑选视频模型
        SELECTED_VID_MODEL = vid_models[0] if vid_models else 'veo-2.0'
    except Exception as e:
        st.error(f"无法获取模型列表: {e}")
        SELECTED_IMG_MODEL = 'imagen-3.0-generate-001'
        SELECTED_VID_MODEL = 'veo-2.0'

# --- 3. 核心功能函数 ---

def get_ai_script(topic):
    """DeepSeek 生成并清洗 JSON"""
    prompt = f"针对'{topic}'生成3个短视频分镜JSON，包含text(文案), visual(画图提示词), camera(运镜)。只输出JSON。"
    try:
        response = ds_client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":prompt}])
        raw = response.choices[0].message.content
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except: return None

def generate_image_auto(desc):
    """使用探测到的模型进行绘图"""
    try:
        # 尝试使用侧边栏自动探测到的模型名
        res = google_client.models.generate_images(
            model=SELECTED_IMG_MODEL, 
            prompt=desc, 
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
        )
        return res.generated_images[0].image_bytes
    except Exception as e:
        st.error(f"绘图失败 ({SELECTED_IMG_MODEL}): {e}")
        return None

def generate_video_auto(img_bytes, cam):
    """使用探测到的模型生成视频"""
    try:
        res = google_client.models.generate_content(
            model=SELECTED_VID_MODEL, 
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), f"Motion: {cam}"]
        )
        return res.candidates[0].content.parts[0].inline_data.data
    except: return None

# --- 4. 运行界面 ---

topic = st.text_input("视频主题：", "小蝌蚪找妈妈")

if st.button("🚀 开始生产"):
    with st.spinner("1. 正在构思脚本..."):
        scenes = get_ai_script(topic)
    
    if scenes:
        for i, s in enumerate(scenes):
            st.divider()
            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                st.info(f"**分镜 {i+1}**\n\n{s['text']}")
                st.caption(f"运镜: {s['camera']}")
            
            img_data = None
            with c2:
                with st.spinner("2. 绘图中..."):
                    img_data = generate_image_auto(s['visual'])
                    if img_data: 
                        st.image(img_data)
                        st.download_button("下图片", img_data, f"img_{i}.jpg", key=f"i{i}")

            with c3:
                if img_data:
                    with st.spinner("3. 渲染视频..."):
                        vid_data = generate_video_auto(img_data, s['camera'])
                        if vid_data: 
                            st.video(vid_data)
                            st.download_button("下视频", vid_data, f"vid_{i}.mp4", key=f"v{i}")
                        else: st.warning(f"当前 Key 暂无 {SELECTED_VID_MODEL} 视频权限")

        st.balloons()
