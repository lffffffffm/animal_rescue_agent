# import os
# import json
# import time
# import hashlib
# from datetime import datetime
# import requests
# from bs4 import BeautifulSoup
# from tqdm import tqdm
# import dashscope
# from markdownify import markdownify as md
# from app.config import settings
# from app.db.base import SessionLocal
# from app.db.knowledge_model import Chunk, Document
# from app.knowledge_base.scripts.generate_urgency import generate_urgency
# from app.knowledge_base.scripts.process_chunks import split_by_headers, refine_chunks
# from app.knowledge_base.scripts.save_document import save_document
# from app.knowledge_base.scripts.translate_md import translate_markdown
# from app.knowledge_base.scripts import logger
#
# dashscope.api_key = settings.LLM_API_KEY
# URL_LIST_FILE = "./article_urls_list.txt"
# PROGRESS_FILE = "./crawl_progress.json"
#
#
# # ===============================
# # 主流程
# # ===============================
# def run_crawl():
#     db = SessionLocal()
#
#     with open(URL_LIST_FILE, "r", encoding="utf-8") as f:
#         urls = [line.strip() for line in f.readlines() if line.strip()]
#
#     progress = {}
#     if os.path.exists(PROGRESS_FILE):
#         with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
#             progress = json.load(f)
#
#     headers = {"User-Agent": "Mozilla/5.0"}
#
#     for url in tqdm(urls, desc="Crawling"):
#
#         if url in progress:
#             logger.warning("已处理, 跳过 | url={}", url)
#             continue
#
#         doc_start_time = time.time()
#         logger.info("开始处理 | url={}", url)
#
#         try:
#             # ===============================
#             # A. 抓取网页
#             # ===============================
#             t0 = time.time()
#             res = requests.get(url, headers=headers, timeout=15)
#             res.raise_for_status()
#             soup = BeautifulSoup(res.content, 'html.parser')
#
#             main_content = soup.find('div', {'data-testid': 'topic-main-content'})
#             if not main_content:
#                 main_content = soup.find('main') or soup.find('article')
#
#             if not main_content:
#                 logger.error("未找到正文内容 | url={}", url)
#                 continue
#
#             # 清洗 HTML
#             # 删除空的 Section
#             for section in main_content.find_all("section"):
#                 if not section.get_text(strip=True):
#                     section.decompose()
#
#             for span in main_content.find_all("span", attrs={"aria-hidden": "true"}):
#                 span.decompose()
#
#             for unwanted in main_content.find_all(
#                     ['nav', 'aside', 'button', 'footer', 'script', 'style']
#             ):
#                 unwanted.decompose()
#
#             for a in main_content.find_all("a"):
#                 a.replace_with(a.get_text())
#
#             logger.info(
#                 "HTML清洗完成 | chars={} | cost={:.2f}s",
#                 len(str(main_content)),
#                 time.time() - t0
#             )
#
#             title_tag = soup.find("h1")
#             page_title = title_tag.get_text(strip=True) if title_tag else soup.title.string.strip()
#             logger.info("标题 | title={}", page_title)
#
#             # ===============================
#             # B. HTML -> Markdown
#             # ===============================
#             t1 = time.time()
#             raw_markdown = md(
#                 str(main_content),
#                 heading_style="ATX",
#                 bullets="-"
#             )
#             raw_markdown = f"# {page_title}\n\n" + raw_markdown
#
#             logger.info(
#                 "Markdown生成完成 | chars={} | preview={} | cost={:.2f}s",
#                 len(raw_markdown),
#                 raw_markdown[:100].replace("\n", " "),
#                 time.time() - t1
#             )
#
#             # ===============================
#             # C. 翻译
#             # ===============================
#             t2 = time.time()
#             chinese_md = translate_markdown(raw_markdown)
#
#             if not chinese_md:
#                 logger.error("翻译失败 | url={}", url)
#                 continue
#
#             logger.info(
#                 "翻译完成 | chars={} | preview={} | cost={:.2f}s",
#                 len(chinese_md),
#                 chinese_md[:100].replace("\n", " "),
#                 time.time() - t2
#             )
#
#             # ===============================
#             # D. 保存 Document
#             # ===============================
#             doc: Document = save_document(db, soup, url)
#             logger.info("Document保存成功 | doc_id={}", doc.id)
#
#             # ===============================
#             # E. 切分 Markdown
#             # ===============================
#             chunk_texts = split_by_headers(chinese_md)
#             chunk_texts = refine_chunks(chunk_texts, max_chars=1000)
#             total = len(chunk_texts)
#
#             logger.info("切分完成 | chunks={}", total)
#
#             # ===============================
#             # F. 生成 chunk + urgency
#             # ===============================
#             for index, text in enumerate(chunk_texts):
#
#                 urgency_start = time.time()
#                 urgency = generate_urgency(text)
#                 urgency_cost = time.time() - urgency_start
#
#                 chunk = Chunk(
#                     id=hashlib.md5(f"{doc.id}_{index}".encode()).hexdigest(),
#                     document_id=doc.id,
#                     content=text,
#                     chunk_index=index,
#                     total_chunks=total,
#                     urgency=urgency,
#                     created_at=datetime.utcnow(),
#                 )
#
#                 logger.info(
#                     "Chunk生成 | doc_id={} | {}/{} | chars={} | urgency={} | urgency_cost={:.2f}s | preview={}",
#                     doc.id,
#                     index + 1,
#                     total,
#                     len(text),
#                     urgency,
#                     urgency_cost,
#                     text[:120].replace("\n", " ")
#                 )
#
#                 db.add(chunk)
#
#             db.commit()
#
#             progress[url] = "done"
#             with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
#                 json.dump(progress, f, ensure_ascii=False, indent=2)
#
#             total_cost = time.time() - doc_start_time
#             logger.success("文档处理完成 | url={} | total_cost={:.2f}s", url, total_cost)
#
#             time.sleep(2)
#
#         except Exception:
#             logger.exception("处理失败 | url={}", url)
#             progress[url] = "failed"
#             with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
#                 json.dump(progress, f, ensure_ascii=False, indent=2)
#             db.rollback()
#             time.sleep(5)
#         break
#
#     db.close()
#
#
# if __name__ == "__main__":
#     run_crawl()


# import os
# import json
# import time
# import hashlib
# from datetime import datetime
# import asyncio
# import aiohttp
# from bs4 import BeautifulSoup
# from tqdm.asyncio import tqdm_asyncio
# import dashscope
# from markdownify import markdownify as md
# from app.config import settings
# from app.db.base import SessionLocal
# from app.db.knowledge_model import Chunk, Document
# from app.knowledge_base.scripts.generate_urgency import generate_urgency
# from app.knowledge_base.scripts.process_chunks import split_by_headers, refine_chunks
# from app.knowledge_base.scripts.save_document import save_document
# from app.knowledge_base.scripts.translate_md import translate_markdown
# from app.knowledge_base.scripts import logger
#
# dashscope.api_key = settings.LLM_API_KEY
# URL_LIST_FILE = "./article_urls_list.txt"
# PROGRESS_FILE = "./crawl_progress.json"
#
# # ===============================
# # 异步抓取网页
# # ===============================
# async def fetch(session, url, retries=3):
#     for attempt in range(retries):
#         try:
#             async with session.get(url, timeout=20) as response:
#                 html = await response.text()
#                 return url, html
#         except Exception as e:
#             logger.warning("请求失败 | url={} | attempt={} | error={}", url, attempt+1, e)
#             await asyncio.sleep(2 + attempt)  # 退避重试
#     return url, None
#
# # ===============================
# # 异步处理单个网页
# # ===============================
# async def process_page(db, url, html, progress):
#     if not html:
#         progress[url] = "failed"
#         return
#
#     try:
#         doc_start_time = time.time()
#         logger.info("开始处理 | url={}", url)
#
#         soup = BeautifulSoup(html, 'html.parser')
#         main_content = soup.find('div', {'data-testid': 'topic-main-content'}) or soup.find('main') or soup.find('article')
#         if not main_content:
#             logger.error("未找到正文内容 | url={}", url)
#             progress[url] = "failed"
#             return
#
#         # 清洗 HTML
#         for section in main_content.find_all("section"):
#             if not section.get_text(strip=True):
#                 section.decompose()
#         for span in main_content.find_all("span", attrs={"aria-hidden": "true"}):
#             span.decompose()
#         for unwanted in main_content.find_all(['nav', 'aside', 'button', 'footer', 'script', 'style']):
#             unwanted.decompose()
#         for a in main_content.find_all("a"):
#             a.replace_with(a.get_text())
#
#         title_tag = soup.find("h1")
#         page_title = title_tag.get_text(strip=True) if title_tag else (soup.title.string.strip() if soup.title else "No Title")
#         logger.info("标题 | title={}", page_title)
#
#         # HTML -> Markdown
#         raw_markdown = md(str(main_content), heading_style="ATX", bullets="-")
#         raw_markdown = f"# {page_title}\n\n" + raw_markdown
#
#         logger.info("Markdown生成完成 | chars={} | preview={}", len(raw_markdown), raw_markdown[:100].replace("\n", " "))
#
#         # 翻译
#         chinese_md = translate_markdown(raw_markdown)
#         if not chinese_md:
#             logger.error("翻译失败 | url={}", url)
#             progress[url] = "failed"
#             return
#
#         logger.info("翻译完成 | chars={} | preview={}", len(chinese_md), chinese_md[:100].replace("\n", " "))
#
#         # 保存 Document
#         doc: Document = save_document(db, soup, url)
#         logger.info("Document保存成功 | doc_id={}", doc.id)
#
#         # 切分 Markdown
#         chunk_texts = split_by_headers(chinese_md)
#         chunk_texts = refine_chunks(chunk_texts, max_chars=1000)
#         total = len(chunk_texts)
#         logger.info("切分完成 | chunks={}", total)
#
#         # 生成 chunk + urgency
#         for index, text in enumerate(chunk_texts):
#             urgency_start = time.time()
#             urgency = generate_urgency(text)
#             urgency_cost = time.time() - urgency_start
#
#             chunk = Chunk(
#                 id=hashlib.md5(f"{doc.id}_{index}".encode()).hexdigest(),
#                 document_id=doc.id,
#                 content=text,
#                 chunk_index=index,
#                 total_chunks=total,
#                 urgency=urgency,
#                 created_at=datetime.utcnow(),
#             )
#             logger.info(
#                 "Chunk生成 | doc_id={} | {}/{} | chars={} | urgency={} | urgency_cost={:.2f}s | preview={}",
#                 doc.id,
#                 index + 1,
#                 total,
#                 len(text),
#                 urgency,
#                 urgency_cost,
#                 text[:120].replace("\n", " ")
#             )
#             db.add(chunk)
#
#         db.commit()
#         progress[url] = "done"
#         with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
#             json.dump(progress, f, ensure_ascii=False, indent=2)
#
#         total_cost = time.time() - doc_start_time
#         logger.success("文档处理完成 | url={} | total_cost={:.2f}s", url, total_cost)
#
#     except Exception:
#         logger.exception("处理失败 | url={}", url)
#         progress[url] = "failed"
#         db.rollback()
#         with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
#             json.dump(progress, f, ensure_ascii=False, indent=2)
#
# # ===============================
# # 主异步流程
# # ===============================
# async def run_async_crawl():
#     db = SessionLocal()
#
#     with open(URL_LIST_FILE, "r", encoding="utf-8") as f:
#         urls = [line.strip() for line in f.readlines() if line.strip()]
#
#     progress = {}
#     if os.path.exists(PROGRESS_FILE):
#         with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
#             progress = json.load(f)
#
#     semaphore = asyncio.Semaphore(5)  # 同时最多5个请求，更稳
#
#     async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
#
#         async def sem_task(url):
#             async with semaphore:
#                 if url in progress and progress[url] == "done":
#                     logger.warning("已处理, 跳过 | url={}", url)
#                     return
#                 url, html = await fetch(session, url)
#                 await process_page(db, url, html, progress)
#                 await asyncio.sleep(1)  # 随机延迟避免被限流
#
#         tasks = [sem_task(url) for url in urls]
#         for coro in tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Crawling"):
#             await coro
#
#     db.close()
#
# # ===============================
# # 入口
# # ===============================
# if __name__ == "__main__":
#     asyncio.run(run_async_crawl())

# ===============================
# 主异步流程
# ===============================
import os
import json
import time
import hashlib
from datetime import datetime
import asyncio
import aiohttp
import dashscope
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from markdownify import markdownify as md
from app.db.base import SessionLocal
from app.db.knowledge_model import Chunk, Document
from app.knowledge_base.scripts.generate_urgency import generate_urgency
from app.knowledge_base.scripts.process_chunks import split_by_headers, refine_chunks
from app.knowledge_base.scripts.save_document import save_document
from app.knowledge_base.scripts import logger
from app.knowledge_base.scripts.translate_md import translate_markdown
from app.config import settings

dashscope.api_key = settings.LLM_API_KEY
URL_LIST_FILE = "./article_urls_list.txt"
PROGRESS_FILE = "./crawl_progress.json"


async def async_translate(text):
    """
    异步执行同步翻译函数，避免阻塞事件循环
    """
    return await asyncio.to_thread(translate_markdown, text)


async def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=20) as response:
                html = await response.text()
                return url, html
        except Exception as e:
            logger.warning("请求失败 | url={} | attempt={} | error={}", url, attempt + 1, e)
            await asyncio.sleep(2 + attempt)  # 退避重试
    return url, None


async def process_page_async(db, url, html, progress):
    if not html:
        progress[url] = "failed"
        return

    try:
        doc_start_time = time.time()
        logger.info("开始处理 | url={}", url)

        soup = BeautifulSoup(html, 'html.parser')
        main_content = soup.find('div', {'data-testid': 'topic-main-content'}) or soup.find('main') or soup.find(
            'article')
        if not main_content:
            logger.error("未找到正文内容 | url={}", url)
            progress[url] = "failed"
            return

        # 清洗 HTML
        for section in main_content.find_all("section"):
            if not section.get_text(strip=True):
                section.decompose()
        for span in main_content.find_all("span", attrs={"aria-hidden": "true"}):
            span.decompose()
        for unwanted in main_content.find_all(['nav', 'aside', 'button', 'footer', 'script', 'style']):
            unwanted.decompose()
        for a in main_content.find_all("a"):
            a.replace_with(a.get_text())

        title_tag = soup.find("h1")
        page_title = title_tag.get_text(strip=True) if title_tag else (
            soup.title.string.strip() if soup.title else "No Title")
        logger.info("标题 | title={}", page_title)

        # HTML -> Markdown
        raw_markdown = md(str(main_content), heading_style="ATX", bullets="-")
        raw_markdown = f"# {page_title}\n\n" + raw_markdown
        logger.info("Markdown生成完成 | chars={} | preview={}", len(raw_markdown),
                    raw_markdown[:100].replace("\n", " "))

        # 异步翻译
        t_translate_start = time.time()
        chinese_md = await async_translate(raw_markdown)
        if not chinese_md:
            logger.error("翻译失败 | url={}", url)
            progress[url] = "failed"
            return
        logger.info("翻译完成 | chars={} | preview={} | cost={:.2f}s", len(chinese_md),
                    chinese_md[:100].replace("\n", " "), time.time() - t_translate_start)

        # 保存 Document
        doc: Document = save_document(db, soup, url)
        logger.info("Document保存成功 | doc_id={}", doc.id)

        # 切分 Markdown
        chunk_texts = split_by_headers(chinese_md)
        chunk_texts = refine_chunks(chunk_texts, max_chars=1000)
        total = len(chunk_texts)
        logger.info("切分完成 | chunks={}", total)

        # 生成 chunk + urgency
        for index, text in enumerate(chunk_texts):
            urgency_start = time.time()
            urgency = generate_urgency(text)
            urgency_cost = time.time() - urgency_start

            chunk = Chunk(
                id=hashlib.md5(f"{doc.id}_{index}".encode()).hexdigest(),
                document_id=doc.id,
                content=text,
                chunk_index=index,
                total_chunks=total,
                urgency=urgency,
                created_at=datetime.utcnow(),
            )
            logger.info(
                "Chunk生成 | doc_id={} | {}/{} | chars={} | urgency={} | urgency_cost={:.2f}s | preview={}",
                doc.id,
                index + 1,
                total,
                len(text),
                urgency,
                urgency_cost,
                text[:120].replace("\n", " ")
            )
            db.add(chunk)

        db.commit()
        progress[url] = "done"
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

        total_cost = time.time() - doc_start_time
        logger.success("文档处理完成 | url={} | total_cost={:.2f}s", url, total_cost)

    except Exception:
        logger.exception("处理失败 | url={}", url)
        progress[url] = "failed"
        db.rollback()
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)


async def run_async_crawl_optimized():
    db = SessionLocal()

    with open(URL_LIST_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]

    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress = json.load(f)

    semaphore = asyncio.Semaphore(20)  # 提高并发数量

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:

        async def sem_task(url):
            async with semaphore:
                if progress.get(url) == "done":
                    logger.warning("已处理, 跳过 | url={}", url)
                    return
                # 抓取网页
                url_fetched, html = await fetch(session, url)
                # 处理页面（含异步翻译）
                await process_page_async(db, url_fetched, html, progress)
                await asyncio.sleep(0.1)  # 避免请求过快

        tasks = [sem_task(url) for url in urls]
        for coro in tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Crawling"):
            await coro

    db.close()


if __name__ == "__main__":
    asyncio.run(run_async_crawl_optimized())
