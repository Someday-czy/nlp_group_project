import streamlit as st
from main import get_ai_response
import conversation_utils as conv_utils
import os
from datetime import datetime


# --- 应用配置 ---
st.set_page_config(
    page_title="AI 对话机器人",
    page_icon="🤖",
    layout="centered",
)


# --- 会话状态初始化 ---
def initialize_session_state():
    """初始化或加载对话。"""
    if "messages" not in st.session_state:
        conv_list = conv_utils.get_conversation_list()
        if conv_list:
            # 加载最新对话
            st.session_state.messages = conv_utils.load_conversation(conv_list[0])
            st.session_state.current_conversation = conv_list[0]
        else:
            # 创建新对话
            st.session_state.messages = conv_utils.get_default_messages("你是一个得力的AI助手。")
            st.session_state.current_conversation = None

        # 无论加载还是新建，都从 messages 初始化 system_prompt
        if st.session_state.messages:
            st.session_state.system_prompt = st.session_state.messages[0].get("content", "你是一个得力的AI助手。")
        else:
            st.session_state.system_prompt = "你是一个得力的AI助手。"


# --- 侧边栏渲染 ---
def render_sidebar():
    """渲染侧边栏UI和逻辑。"""

    def on_prompt_change():
        """当系统提示词变化时，保存到当前对话中。"""
        st.session_state.messages[0]["content"] = st.session_state.system_prompt
        if st.session_state.current_conversation:
            conv_utils.save_conversation(st.session_state.messages, filename=st.session_state.current_conversation)
            st.toast("系统提示词已更新并保存！")

    with st.sidebar:
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] > div:first-child {
                    padding-top: 1rem;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # 1. Logo
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.title("🤖 AI 对话")

        # 2. 开启新对话按钮
        if st.button("➕ 开启新对话", use_container_width=True):
            st.session_state.messages = conv_utils.get_default_messages("你是一个得力的AI助手。")
            st.session_state.current_conversation = None
            st.session_state.system_prompt = "你是一个得力的AI助手。"
            st.rerun()

        st.markdown("---")

        # 3. 对话列表
        grouped_conversations = conv_utils.get_grouped_conversations()
        for group_name, filenames in grouped_conversations.items():
            if filenames:
                st.markdown(f"**{group_name}**")
                for filename in filenames:
                    title = conv_utils.get_title_from_filename(filename)
                    # 检查当前对话是否为选中对话，以决定按钮样式
                    is_selected = (filename == st.session_state.get("current_conversation"))
                    # button_type = "primary" if is_selected else "secondary"

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(title, key=f"load_{filename}", use_container_width=True, type="primary" if is_selected else "secondary"):
                            # 仅当点击的不是当前已选中的对话时才重新加载，避免不必要的操作
                            if not is_selected:
                                loaded_messages = conv_utils.load_conversation(filename)
                                if loaded_messages:
                                    st.session_state.messages = loaded_messages
                                    st.session_state.current_conversation = filename
                                    st.session_state.system_prompt = loaded_messages[0].get("content",
                                                                                            "你是一个得力的AI助手。")
                                st.rerun()
                    with col2:
                        if st.button("🗑️", key=f"delete_{filename}", use_container_width=True, type="secondary"):
                            conv_utils.delete_conversation(filename)
                            if st.session_state.get("current_conversation") == filename:
                                st.session_state.current_conversation = None
                                st.session_state.messages = conv_utils.get_default_messages(
                                    st.session_state.system_prompt)
                            st.rerun()

        st.markdown("---")
        # 4. 系统提示词设置
        st.text_area(
            "系统提示词",
            key="system_prompt",
            on_change=on_prompt_change
        )


# --- 主函数 ---
def main():
    initialize_session_state()
    render_sidebar()

    st.title("🤖 多轮对话聊天机器人")

    # --- 显示历史消息 ---
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # --- 聊天输入框 ---
    if prompt := st.chat_input("你好！"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            ai_response_stream = get_ai_response(st.session_state.messages)
            full_response = st.write_stream(ai_response_stream)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # --- 自动保存与标题生成 ---
        is_new_conversation = not st.session_state.get(
            "current_conversation") or st.session_state.current_conversation.startswith("新对话")

        if is_new_conversation and len(st.session_state.messages) == 3:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"新对话_{timestamp}.json"
            conv_utils.save_conversation(st.session_state.messages, filename=default_filename)
            st.session_state.current_conversation = default_filename
            st.toast("新对话已创建！正在生成标题...")

            try:
                summary_prompt = f"请为以下对话生成一个不超过8个字的简短标题：\n\n用户：{prompt}\nAI：{full_response}"
                title_messages = [{"role": "system", "content": "你是一个文本摘要和标题生成专家。"},
                                  {"role": "user", "content": summary_prompt}]
                title_stream = get_ai_response(title_messages)
                title = "".join(list(title_stream)).strip().replace("\n", " ").replace("/", "_")

                if title:
                    new_filename = f"{title}_{timestamp}.json"
                    rename_success = conv_utils.rename_conversation(default_filename, new_filename)
                    if rename_success:
                        # 关键：更新 session_state 中的文件名
                        st.session_state.current_conversation = new_filename
                        # 关键：重新加载消息（确保文件名已更新）
                        st.session_state.messages = conv_utils.load_conversation(new_filename)
                        st.toast(f"对话标题已更新: {title}")
                        # 立即停止执行，让 Streamlit 完全重新渲染
                        st.rerun()
                    else:
                        st.warning("重命名文件失败，已保留默认标题。")
                else:
                    st.warning("未能生成有效标题，已保留默认标题。")
            except Exception as e:
                st.error(f"生成标题时出错: {e}")
                st.warning("已使用默认标题保存对话。")
        else:
            if st.session_state.current_conversation:
                conv_utils.save_conversation(st.session_state.messages, filename=st.session_state.current_conversation)
                st.toast("对话已更新。")

        st.rerun()


if __name__ == "__main__":
    main()