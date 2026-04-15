import streamlit as st
import conversation_utils as conv_utils
import os
from datetime import datetime
from langchain_chat import chain_with_memory, get_session_history
from langchain_core.messages import HumanMessage, AIMessage
import re
import time

# --- 应用配置 ---
st.set_page_config(
    page_title="AI 对话机器人 (LangChain)",
    page_icon="🔗",
    layout="centered",
)

# --- 会话状态初始化 ---
def initialize_session_state():
    """初始化或加载对话，适配LangChain。"""
    if "history" not in st.session_state:
        conv_list = conv_utils.get_conversation_list()
        if conv_list:
            # 加载最新对话
            st.session_state.current_conversation = conv_list[0]
            history, system_prompt = conv_utils.load_conversation(conv_list[0])
            st.session_state.history = history
            st.session_state.system_prompt = system_prompt
        else:
            # 创建新对话
            st.session_state.current_conversation = None
            st.session_state.history = get_session_history("new_chat") # 使用默认session_id
            st.session_state.system_prompt = conv_utils.get_default_system_prompt()

# --- 侧边栏逻辑 ---
def handle_system_prompt_change():
    """处理系统提示词变化的逻辑。"""
    new_prompt = st.session_state.system_prompt_input
    if st.session_state.system_prompt != new_prompt:
        st.session_state.system_prompt = new_prompt
        if st.session_state.get("current_conversation"):
            new_filename = conv_utils.save_conversation(
                st.session_state.system_prompt,
                st.session_state.history,
                st.session_state.current_conversation
            )
            st.session_state.current_conversation = new_filename
            st.toast("系统提示词已更新并保存！")
            st.rerun()
        else:
            st.toast("系统提示词已更新！")

# --- 侧边栏渲染 ---
def render_sidebar():
    """渲染侧边栏UI。"""
    with st.sidebar:
        st.title("🔗 AI 对话 (LangChain)")

        if st.button("➕ 开启新对话", use_container_width=True):
            st.session_state.current_conversation = None
            st.session_state.history = get_session_history("new_chat")
            st.session_state.system_prompt = conv_utils.get_default_system_prompt()
            st.rerun()

        st.markdown("---")

        conversation_list = conv_utils.get_conversation_list()
        if conversation_list:
            try:
                current_index = conversation_list.index(st.session_state.current_conversation)
            except (ValueError, AttributeError):
                current_index = 0

            selected_conversation = st.selectbox(
                "选择一个对话",
                conversation_list,
                index=current_index,
                format_func=conv_utils.get_title_from_filename,
                key="conversation_selector"
            )

            if selected_conversation and selected_conversation != st.session_state.current_conversation:
                history, system_prompt = conv_utils.load_conversation(selected_conversation)
                st.session_state.history = history
                st.session_state.system_prompt = system_prompt
                st.session_state.current_conversation = selected_conversation
                st.rerun()

            if st.button("🗑️ 删除当前对话", use_container_width=True):
                if st.session_state.current_conversation:
                    conv_utils.delete_conversation(st.session_state.current_conversation)
                    st.session_state.current_conversation = None
                    st.session_state.history = get_session_history("new_chat_after_delete")
                    st.session_state.system_prompt = conv_utils.get_default_system_prompt()
                    st.rerun()

        st.markdown("---")
        st.text_area(
            "系统提示词",
            value=st.session_state.system_prompt,
            key="system_prompt_input",
            on_change=handle_system_prompt_change
        )

# --- 主函数 ---
def main():
    initialize_session_state()
    render_sidebar()

    st.title("🔗 多轮对话聊天机器人")

    # --- 显示历史消息 ---
    for msg in st.session_state.history.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)

    # --- 聊天输入框 ---
    if prompt := st.chat_input("你好！"):
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            session_id = st.session_state.get("current_conversation", "new_chat")
            get_session_history(session_id).messages = st.session_state.history.messages

            ai_response_stream = chain_with_memory.stream(
                {"system_prompt": st.session_state.system_prompt, "input": prompt},
                config={"configurable": {"session_id": session_id}}
            )
            full_response = st.write_stream(ai_response_stream)

        # --- 自动保存与标题生成 ---
        is_new_conversation = not st.session_state.get("current_conversation")

        new_filename = conv_utils.save_conversation(
            st.session_state.system_prompt,
            st.session_state.history,
            st.session_state.get("current_conversation")
        )
        st.session_state.current_conversation = new_filename

        if is_new_conversation and len(st.session_state.history.messages) == 2:
            st.toast("新对话已创建！正在生成标题...")
            try:
                title_prompt = f"请为以下对话生成一个不超过8个字的简短标题：\n\n用户：{prompt}\nAI：{full_response}"
                title_chain_response = chain_with_memory.invoke(
                    {"system_prompt": "你是一个文本摘要和标题生成专家。", "input": title_prompt},
                    config={"configurable": {"session_id": "title_generation"}}
                )
                title = title_chain_response.strip().replace("\n", " ").replace("/", "_")

                if title:
                    final_filename = conv_utils.rename_conversation(new_filename, title)
                    if final_filename:
                        st.session_state.current_conversation = final_filename
                        st.toast(f"对话标题已更新: {title}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("未能生成有效标题，已保留默认标题。")
            except Exception as e:
                st.error(f"生成标题时出错: {e}")
                st.warning("已使用默认标题保存对话。")
        else:
            st.toast("对话已更新。")
            time.sleep(0.5)
            st.rerun()

if __name__ == "__main__":
    main()