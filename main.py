from openai import OpenAI
import os

# 初始化OpenAI客户端
client = OpenAI(
    # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def get_ai_response(messages):
    """
    调用AI模型获取响应，以流式返回。

    :param messages: 对话历史列表，例如:
                     [{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": "Hello!"}]
    :return: 一个生成器，逐块产出AI模型的回复内容。
    """
    completion = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=messages,
        # 通过 extra_body 设置 enable_thinking 开启思考模式
        extra_body={"enable_thinking": True},
        stream=True,
        stream_options={
            "include_usage": True
        },
    )

    for chunk in completion:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            yield delta.content

if __name__ == '__main__':
    # --- 以下是用于直接运行 main.py 时进行测试的代码 ---
    test_messages = [{"role": "user", "content": "你是谁"}]
    print(f"用户: {test_messages[-1]['content']}")

    print(f"AI: ", end="")
    ai_response_stream = get_ai_response(test_messages)
    full_response = ""
    for chunk in ai_response_stream:
        print(chunk, end="", flush=True)
        full_response += chunk
    print()

    # 模拟第二轮对话
    test_messages.append({"role": "assistant", "content": full_response})
    test_messages.append({"role": "user", "content": "你来自哪里？"})
    print(f"用户: {test_messages[-1]['content']}")
    
    print(f"AI: ", end="")
    ai_response_stream_2 = get_ai_response(test_messages)
    full_response_2 = ""
    for chunk in ai_response_stream_2:
        print(chunk, end="", flush=True)
        full_response_2 += chunk
    print()