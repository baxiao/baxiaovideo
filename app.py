import streamlit as st
import os
import json
import re
import requests

# --- 0. 自动检查依赖环境 ---
try:
    from openai import OpenAI
    from volcenginesdkarkruntime import Ark
except ImportError:
    st.error("⚠️ 依赖库尚未就绪，请确保 requirements.txt 已提交并等待部署完成。")
    st.stop()

# --- 1. 初始化客户端 ---
try:
    # DeepSeek 客户端
    ds_client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"], 
        base_url="https://api.deepseek.com"
    )
    
    # 豆包/火山引擎客户端
    ark_client = Ark(
        ak=st.secrets["VOLC_ACCESS_KEY"],
        sk=st.secrets["VOLC_SECRET_KEY"]
    )
    
    IMG_EP = st.secrets["DOUBAO_IMAGE_ENDPOINT"]
    VID_EP = st.secrets.get("DOUBAO_VIDEO_ENDPOINT", "")
except Exception as e:
    st.error(f"❌ 配置文件错误: {e}")
    st.stop()

st.set_page_config(page_title="豆包全自动视频工厂", layout="wide")
st.title("🎬 豆包 x DeepSeek 视频工厂")
st.caption("由 DeepSeek 策划文案，豆包 (Doubao) 生成视觉素材")

# --- 2. 核心逻辑函数 ---

def get_ai_script(topic):
    """使用 DeepSeek 生成结构化分镜脚本"""
    prompt = f"""
    请为主题“{topic}”创作一个3分镜的短视频脚本。
    必须严格返回 JSON 数组格式，包含以下字段：
    "text": 旁白内容,
    "visual": 画面详细描述 (Prompt),
    "camera": 运镜指令 (英文).
    """
    try:
        response = ds_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        # 强力清洗 JSON 杂质
        match = re.search(r'\[.*\]', content, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"脚本解析失败: {e}")
        return None

def generate_doubao_img(visual_desc):
    """调用豆包模型生成图片"""
    try:
        # 注意：此处使用火山引擎 Ark SDK 的图像生成接口
        response = ark_client.content_generation.create(
            model=IMG_EP,
            prompt=visual_desc,
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"豆包绘图失败: {e}")
        return None

def generate_doubao_vid(img_url, camera_move):
    """调用豆包模型生成视频"""
    if not VID_EP:
        return None
    try:
        # 豆包视频模型通常支持图生视频
        response = ark_client.video_generation.create(
            model=VID_EP,
            image_url=img_url,
            prompt=f"Cinematic video, motion: {camera_move}"
        )
        return response.data[0].url
    except Exception as e:
        st.warning(f"视频生成暂不可用: {e}")
        return None

# --- 3. 界面展示 ---

user_input = st.text_input("请输入视频主题：", placeholder="例如：水墨风的江南烟雨")

if st.button("🚀 启动自动化流水线"):
    if not user_input:
        st.warning("请先输入主题")
    else:
        with st.spinner("1. DeepSeek 正在策划脚本..."):
            scenes = get_ai_script(user_input)
            
        if scenes:
            for i, scene in enumerate(scenes):
                st.divider()
                st.subheader(f"分镜 #{i+1}")
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    st.info(f"**旁白文案：**\n{scene['text']}")
                    st.write(f"🎥 **运镜：** {scene['camera']}")
                    st.text_area(f"复制文案 {i+1}", scene['text'], height=80, key=f"t_{i}")

                current_img_url = None
                with col2:
                    with st.spinner("2. 豆包绘图中..."):
                        current_img_url = generate_doubao_img(scene['visual'])
                        if current_img_url:
                            st.image(current_img_url, caption="豆包生成分镜图")
                            # 下载按钮
                            img_res = requests.get(current_img_url).content
                            st.download_button("📥 下载图片", img_res, f"img_{i}.jpg", key=f"di_{i}")

                with col3:
                    if current_img_url:
                        with st.spinner("3. 豆包视频合成中..."):
                            video_url = generate_doubao_vid(current_img_url, scene['camera'])
                            if video_url:
                                st.video(video_url)
                                video_res = requests.get(video_url).content
                                st.download_button("📥 下载视频", video_res, f"vid_{i}.mp4", key=f"dv_{i}")
                            else:
                                st.write("🎥 视频生成需要对应的 Endpoint 权限")

            st.balloons()
