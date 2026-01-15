import streamlit as st
import os
import requests
import json
import re
from openai import OpenAI
from google import genai
from google.genai import types

# --- 1. 配置读取 ---
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
    GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception as e:
    st.error("❌ 未在 Secrets 中找到 API Key，请检查配置。")
    st.stop()

# 初始化客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
google_client = genai.Client(api_key=GOOGLE_KEY)

st.set_page_config(page_title="AI视频工厂-兼容版", layout="wide")
st.title("🎬 真实全自动视频工厂")

# --- 2. 核心功能函数（带自动容错） ---

def get_ai_script(topic):
    """调用 DeepSeek 生成脚本并强力清洗 JSON"""
    prompt = f"请为主题“{topic}”创作短视频脚本。严格返回JSON数组，包含text, visual, camera字段。不要碎碎念。"
    try:
        response = ds_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = response.choices[0].message.content
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        clean_json = match.group(0) if match else raw_content
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"脚本解析失败: {e}")
        return None

def generate_image_real(visual_desc):
    """尝试多种可能的模型名称来生成图片，解决 404 问题"""
    # 按照 Google 可能的模型代号排序
    possible_models = [
        'imagen-3.0-generate-001', 
        'imagen-3.0-fast-001', 
        'imagen-3.0-capability-001'
    ]
    
    for model_name in possible_models:
        try:
            response = google_client.models.generate_images(
                model=model_name,
                prompt=visual_desc,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    output_mime_type="image/jpeg"
                )
            )
            return response.generated_images[0].image_bytes
        except Exception:
            continue # 这个名字不行，试下一个
    
    raise Exception("所有 Imagen 模型代号均不可用，请检查 AI Studio 权限。")

def generate_video_real(image_bytes, camera_movement):
    """生成视频，增加权限检查"""
    try:
        response = google_client.models.generate_content(
            model='veo-2.0', # 如果这里报错，说明你账号没 Veo 权限
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                f"Movement: {camera_movement}"
            ]
        )
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e:
        raise Exception(f"视频模型(Veo)调用失败: {str(e)}")

# --- 3. 界面逻辑 ---

user_topic = st.text_input("请输入视频主题：", "深海中的发光生物")

if st.button("🚀 启动全自动化生产"):
    if user_topic:
        with st.spinner("正在策划脚本..."):
            scenes = get_ai_script(user_topic)
        
        if scenes:
            for i, scene in enumerate(scenes):
                st.divider()
                st.subheader(f"分镜 #{i+1}")
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    st.write("**文案：**")
                    st.info(scene['text'])
                    st.write(f"**运镜：** {scene['camera']}")
                    st.text_area(f"复制文案 {i+1}", value=scene['text'], key=f"t_{i}")

                img_bytes = None
                with col2:
                    with st.spinner("绘图中..."):
                        try:
                            img_bytes = generate_image_real(scene['visual'])
                            st.image(img_bytes)
                            st.download_button("下载图片", img_bytes, f"img_{i}.jpg", key=f"di_{i}")
                        except Exception as e:
                            st.error(f"图片失败: {e}")

                with col3:
                    if img_bytes:
                        with st.spinner("视频合成中..."):
                            try:
                                video_data = generate_video_real(img_bytes, scene['camera'])
                                st.video(video_data)
                                st.download_button("下载视频", video_data, f"vid_{i}.mp4", key=f"dv_{i}")
                            except Exception as e:
                                st.warning("视频生成暂不可用（可能无 Veo 权限）")
                                st.caption(f"错误详情: {e}")

            st.balloons()
