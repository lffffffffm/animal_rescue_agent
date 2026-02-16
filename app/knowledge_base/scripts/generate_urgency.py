from http import HTTPStatus
import dashscope


def generate_urgency(text):
    prompt = f"""
    请判断以下宠物医疗文本的紧急程度：
    - critical：需要立即处理或紧急送医
    - common：常规处理建议
    - info：介绍性知识

    只返回一个单词。

    文本：
    {text[:2000]}
    """

    response = dashscope.Generation.call(
        model='qwen-plus',
        messages=[{'role': 'user', 'content': prompt}],
        result_format='message'
    )

    if response.status_code == HTTPStatus.OK:
        result = response.output.choices[0].message.content.strip().lower()
        if result in ["critical", "common", "info"]:
            return result

    return "info"