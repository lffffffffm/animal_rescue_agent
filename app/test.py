from app.llm import get_llm

print(get_llm().invoke([
        "用户：请写一个关于机器学习的小文章",
        "小助手："
    ]))