import streamlit as st
import os
import requests
import json
from openai import OpenAI
from google import genai
from google.genai import types

# --- 1. 配置读取 (Streamlit Secrets) ---
DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]

# 初始化 API 客户端
ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
# 这里的 Nano Banana 和 Veo 统称为 Google GenAI 功能
google_client = genai.Client(api_key=GOOGLE_KEY)

st.set_page_config(page_title="真实全自动视频工厂", layout="wide")
st.title("🎬 真实全自动视频工厂")

# --- 2. 核心执行函数 ---

def get_ai_script(topic):
    """调用 DeepSeek 生成分镜脚本数据"""
    prompt = f"""
    请为主题“{topic}”创作短视频脚本。
    必须严格以 JSON 数组格式返回，不要包含代码块标记或解释文字。
    每个对象包含：
    "text": 文案,
    "visual": 详细画面描述（用于AI绘图）,
    "camera": 运镜指令（英文，如 Pan left, Zoom in）
    """
    response = ds_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    # 清理可能存在的 markdown 标签
    content = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
    return json.loads(content)

def generate_image_real(visual_desc):
    """调用 Nano Banana (Imagen 3) 生成图片字节流"""
    # 也可以使用 'imagen-3.0-fast-001' 速度更快
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
    """调用 Veo 生成视频字节流"""
    # 使用 Google 最新视频模型
    response = google_client.models.generate_content(
        model='veo-2.0', 
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            f"Generate a video with this movement: {camera_movement}"
        ]
    )
    # 获取视频二进制数据
    return response.candidates[0].content.parts[0].inline_data.data

# --- 3. 页面交互逻辑 ---

user_topic = st.text_input("请输入视频主题：", "小蝌蚪找妈妈")

if st.button("🚀 启动真实生成任务"):
    if not user_topic:
        st.error("请输入主题后再启动")
    else:
        try:
            # 第一步：DeepSeek 生成脚本列表
            with st.spinner("1. DeepSeek 正在策划分镜脚本..."):
                scenes = get_ai_script(user_topic)
                st.success(f"策划完成，共计 {len(scenes)} 个分镜。")

            # 第二步：循环生成图片和视频
            for i, scene in enumerate(scenes):
                st.divider()
                st.subheader(f"分镜 {i+1}")
                
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    st.write("**文案内容：**")
                    st.info(scene['text'])
                    st.write(f"**运镜：** {scene['camera']}")

                with col2:
                    with st.spinner("2. Nano Banana 正在绘图..."):
                        img_bytes = generate_image_real(scene['visual'])
                        st.image(img_bytes, caption="AI 生成的分镜图")
                        st.download_button("下载图片", img_bytes, f"img_{i}.jpg", "image/jpeg", key=f"img_dl_{i}")

                with col3:
                    with st.spinner("3. Veo 正在生成视频..."):
                        video_data = generate_video_real(img_bytes, scene['camera'])
                        st.video(video_data)
                        st.download_button("下载视频", video_data, f"vid_{i}.mp4", "video/mp4", key=f"vid_dl_{i}")

            st.balloons()
            
        except Exception as e:
            st.error(f"运行出错：{str(e)}")
            st.write("请检查 Secrets 中的 Key 是否有效，以及 Google 账号是否有 Veo 模型权限。")
