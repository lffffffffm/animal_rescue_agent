import re


# 根据md中的标题切分chunk，同时保留标题前的#
def split_by_headers(markdown_text):
    # 使用正则捕获标题：保留#号
    pattern = r'(#{1,6} .+?)\n'
    # 找到所有标题的位置
    headers = [(m.start(), m.group(1)) for m in re.finditer(pattern, markdown_text)]

    chunks = []

    if not headers:
        # 没有标题时直接返回全文
        return [markdown_text.strip()]

    # 遍历每个标题，把每个标题及其内容作为一个chunk
    for i, (pos, header) in enumerate(headers):
        start = pos
        end = headers[i + 1][0] if i + 1 < len(headers) else len(markdown_text)
        chunk = markdown_text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)

    return chunks


# 拆分长 chunk，保留标题 + 上下文 overlap
def refine_chunks(chunk_texts, max_chars=1000, overlap_chars=100):
    refined = []

    for chunk in chunk_texts:
        if len(chunk) <= max_chars:
            refined.append(chunk)
            continue

        # 提取开头标题（可能多行）
        header_match = re.match(r'(\n?#{1,6} .+?\n)+', chunk)
        header = header_match.group(0) if header_match else ""

        body = chunk[len(header):].strip()
        paragraphs = body.split("\n\n")
        temp = header  # 每个 chunk 都从标题开始

        for para in paragraphs:
            if len(temp) + len(para) < max_chars:
                temp += para + "\n\n"
            else:
                if temp.strip():
                    refined.append(temp.strip())

                # 如果单段过长，再按句子拆
                if len(para) > max_chars:
                    sentences = re.split(r'(。|！|？|\.)', para)
                    sentence_block = header  # 每个拆分的子 chunk 也加标题

                    for s in sentences:
                        if len(sentence_block) + len(s) < max_chars:
                            sentence_block += s
                        else:
                            if refined and overlap_chars > 0:
                                overlap = refined[-1][-overlap_chars:]
                                sentence_block = header + overlap + sentence_block[len(header):]
                            refined.append(sentence_block.strip())
                            sentence_block = header + s

                    if sentence_block.strip():
                        if refined and overlap_chars > 0:
                            overlap = refined[-1][-overlap_chars:]
                            sentence_block = header + overlap + sentence_block[len(header):]
                        refined.append(sentence_block.strip())

                    temp = header
                else:
                    temp = header + para + "\n\n"

        if temp.strip():
            if refined and overlap_chars > 0:
                overlap = refined[-1][-overlap_chars:]
                temp = header + overlap + temp[len(header):]
            refined.append(temp.strip())

    return refined