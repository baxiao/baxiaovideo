import streamlit as st
import os
import requests
import json
import re
import time
from openai import OpenAI
from google import genai
from google.genai import types

# --- 1. 配置读取 (从 Streamlit Secrets 加载) ---
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
    GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception as e:
    st.error("❌ 未在 Secrets 中找到 API Key，请检查配置。")
    st.stop()

# 初始化 API 客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
google_client = genai.Client(api_key=GOOGLE_KEY)

st.set_page_config(page_title="AI视频全链路工厂", layout="wide")
st.title("🎬 真实全自动视频工厂")
st.caption("集成 DeepSeek 文案、Nano Banana 绘图、Veo 视频生成")

# --- 2. 核心逻辑函数 ---

def get_ai_script(topic):
    """调用 DeepSeek 生成并清洗 JSON 脚本"""
    prompt = f"""
    请为主题“{topic}”创作短视频脚本。
    必须严格返回一个 JSON 数组，不要任何开场白。
    数组内每个对象包含：
    "text": (短视频旁白文案),
    "visual": (详细的画面描述，英文为主),
    "camera": (运镜指令，如: Pan left, Zoom in, Cinematic motion)
    """
    response = ds_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    raw_content = response.choices[0].message.content
    
    # 【核心修复】使用正则表达式提取 JSON 数组部分，防止 Expecting value 报错
    try:
        match = re.search(r'\[.*\]', raw_content, re.DOTALL)
        if match:
            clean_json = match.group(0)
        else:
            clean_json = raw_content.strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"解析脚本失败。AI返回内容：{raw_content}")
        return None

def generate_image_real(visual_desc):
    """调用 Nano Banana (Imagen 3) 生成图片流"""
    response = google_client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt=visual_desc,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="16:9",
            output_mime_type="image/jpeg"
        )
    )
    return response.generated_images[0].image_bytes

def generate_video_real(image_bytes, camera_movement):
    """调用 Veo 生成视频流"""
    # 结合图片和运镜指令发送给视频模型
    response = google_client.models.generate_content(
        model='veo-2.0', 
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            f"Generate a cinematic video based on this image with movement: {camera_movement}"
        ]
    )
    return response.candidates[0].content.parts[0].inline_data.data

# --- 3. 页面交互 ---

user_topic = st.text_input("请输入视频主题（如：赛博朋克风的成都街头）：")

if st.button("🚀 开启全自动化生产线"):
    if not user_topic:
        st.warning("请先输入主题内容")
    else:
        # 第一步：生成脚本
        with st.spinner("1/3 DeepSeek 正在策划脚本..."):
            scenes = get_ai_script(user_topic)
        
        if scenes:
            st.success(f"✅ 脚本策划完成，共计 {len(scenes)} 个分镜")
            
            # 第二步：根据脚本数量循环处理
            for i, scene in enumerate(scenes):
                st.markdown(f"---")
                st.subheader(f"分镜 #{i+1}")
                
                col_txt, col_img, col_vid = st.columns([1, 2, 2])
                
                with col_txt:
                    st.markdown("**📜 旁白文案**")
                    st.info(scene['text'])
                    st.write(f"🎥 **运镜:** {scene['camera']}")
                    # 方便文哥复制
                    st.text_area(f"复制文案 {i+1}", value=scene['text'], height=80, key=f"txt_{i}")

                # 定义图片变量供视频生成使用
                current_img_bytes = None

                with col_img:
                    with st.spinner("2/3 Nano Banana 绘图中..."):
                        try:
                            current_img_bytes = generate_image_real(scene['visual'])
                            st.image(current_img_bytes, caption="生成的分镜母图")
                            st.download_button("📥 下载图片", current_img_bytes, f"img_{i+1}.jpg", "image/jpeg", key=f"dl_img_{i}")
                        except Exception as e:
                            st.error(f"图片生成失败: {e}")

                with col_vid:
                    if current_img_bytes:
                        with st.spinner("3/3 Veo 正在合成运镜视频..."):
                            try:
                                video_bytes = generate_video_real(current_img_bytes, scene['camera'])
                                st.video(video_bytes)
                                st.download_button("📥 下载视频", video_bytes, f"vid_{i+1}.mp4", "video/mp4", key=f"dl_vid_{i}")
                            except Exception as e:
                                st.error(f"视频生成失败: {e}")
                                st.info("提示：请检查 Google 账号是否已获得 Veo 2.0 模型的使用权限。")
            
            st.balloons()
