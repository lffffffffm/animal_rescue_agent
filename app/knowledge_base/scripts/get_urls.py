# 统计并获取本地知识库需要的文章链接
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def count_msd_with_expand_all(url, label):
    with sync_playwright() as p:
        print(f"🔍 正在连接 {label}...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            print(f"🖱️ 正在定位 'Expand all' 按钮...")
            expand_btn = page.locator('button[data-testid="expandAllFilter"]')

            if expand_btn.count() == 0:
                expand_btn = page.get_by_role("button", name="Expand all", exact=False)

            if expand_btn.count() > 0:
                expand_btn.first.click()
                print(f"✅ 已点击展开！正在等待列表渲染...")
                page.wait_for_timeout(5000)
            else:
                print(f"⚠️ 未找到展开按钮，尝试向下滚动触发加载...")
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(3000)

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            unique_links = set()

            # 统一路径前缀识别
            if "cat-owners" in url:
                path_key = "/cat-owners/"
            elif "dog-owners" in url:
                path_key = "/dog-owners/"
            elif "special-pet-topics" in url:
                path_key = "/special-pet-topics/"
            elif "all-other-pets" in url:
                path_key = "/all-other-pets/"
            else:
                path_key = "/pet-owners/"

            for a in soup.find_all('a', href=True):
                href = a['href']
                # 剔除锚点(#)和参数(?)
                base_href = href.split('#')[0].split('?')[0]

                if path_key in base_href:
                    # 核心修改：计算路径深度
                    # 示例: /cat-owners/behavior-of-cats/social-behavior-of-cats -> ['', 'cat-owners', 'behavior-of-cats', 'social-behavior-of-cats']
                    segments = [s for s in base_href.split('/') if s]

                    # --- 关键逻辑：过滤目录页 ---
                    # 1. 常规猫狗和异宠专栏，文章深度通常 >= 3
                    # 2. 专题(special-pet-topics)有的文章深度可能从 2 开始，但通常也是 3
                    # 我们设置为 >= 3 可以完美剔除类似 /cat-owners/behavior-of-cats 这种中间目录
                    if len(segments) >= 3:
                        full_url = f"https://www.msdvetmanual.com{base_href}" if base_href.startswith(
                            '/') else base_href

                        # 排除掉各个主专栏的入口 URL
                        if not full_url.strip('/').endswith(
                                ('cat-owners', 'dog-owners', 'special-pet-topics', 'all-other-pets')):
                            unique_links.add(full_url)

            print(f"✅ {label} 统计完成: 共发现 {len(unique_links)} 条纯净文章链接")
            return list(unique_links)

        except Exception as e:
            print(f"❌ {label} 抓取异常: {e}")
            return []
        finally:
            browser.close()


def main():
    tasks = [
        ("https://www.msdvetmanual.com/cat-owners", "猫专栏"),
        ("https://www.msdvetmanual.com/dog-owners", "狗专栏"),
        ("https://www.msdvetmanual.com/special-pet-topics", "专题/急救/中毒专栏"),
        ("https://www.msdvetmanual.com/all-other-pets", "异宠专栏")
    ]

    all_links = []
    summary = {}

    for url, label in tasks:
        links = count_msd_with_expand_all(url, label)
        all_links.extend(links)
        summary[label] = len(links)

    final_links = list(set(all_links))

    print("\n" + "=" * 45)
    print(f"📊 【本地知识库】规模确认：")
    for label, count in summary.items():
        print(f"   - {label}: {count} 篇")
    print("-" * 45)
    print(f"   🔥 最终过滤目录后的文章总数: {len(final_links)}")
    print("=" * 45)

    if final_links:
        # 使用当前目录下的文件名
        file_path = os.path.abspath("./article_urls_list.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            for link in final_links:
                f.write(link + "\n")
        print(f"📝 纯净文章任务清单已保存至: {file_path}")


# if __name__ == "__main__":
#     main()
