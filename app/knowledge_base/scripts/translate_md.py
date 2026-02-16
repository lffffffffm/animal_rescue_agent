# 翻译markdown
from http import HTTPStatus
import dashscope


def translate_markdown(raw_markdown):
    prompt = f"""
    你是一名资深兽医专家。

    请将以下英文 Markdown 内容翻译成专业中文：
    1. 严格保留原 Markdown 标题层级。
    2. 不重写结构。
    3. 删除广告导航等无关内容。
    4. 不添加解释。

    内容：
    {raw_markdown}
    """

    response = dashscope.Generation.call(
        model='qwen-plus',
        messages=[{'role': 'user', 'content': prompt}],
        result_format='message'
    )

    if response.status_code == HTTPStatus.OK:
        return response.output.choices[0].message.content

    return None
