import streamlit as st
from main import get_ai_response

st.set_page_config(
    page_title="多轮对话聊天机器人",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 多轮对话聊天机器人")

# --- 初始化 session state ---
# "messages" 键用于存储整个对话历史
if "messages" not in st.session_state:
    # 初始时可以给AI一个系统级的指令
    st.session_state.messages = [{"role": "system", "content": "你是一个得力的AI助手。"}]

# --- 显示历史消息 ---
# 遍历 session_state 中除了系统指令外的所有消息，并用聊天气泡显示出来
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- 聊天输入框 ---
if prompt := st.chat_input("你好！"):
    # 1. 将用户的输入添加到对话历史中
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. 在界面上显示用户的输入
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. 调用AI模型获取回复并以流式显示
    with st.chat_message("assistant"):
        # 调用在 main.py 中定义的生成器函数
        ai_response_stream = get_ai_response(st.session_state.messages)
        
        # 使用 st.write_stream 来实时渲染流式响应
        # 并将完整的响应保存下来
        full_response = st.write_stream(ai_response_stream)

    # 4. 将AI的完整回复也添加到对话历史中
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    print(st.session_state.messages)