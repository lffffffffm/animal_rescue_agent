from typing import List, Dict
import numpy as np
from app.mcp.web_search.schemas import WebFact
from app.knowledge_base.embedding_manager import get_embedding
from urllib.parse import urlparse

DOMAIN_CONFIDENCE = {
    "gov.cn": 0.95,
    "edu.cn": 0.90,
    "baike.baidu.com": 0.85,
    "zhihu.com": 0.75,
    "mp.weixin.qq.com": 0.70,
    "weibo.com": 0.60
}


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def source_prior(url: str) -> float:
    """来源可信度（0~1）"""
    domain = urlparse(url).netloc
    for k, v in DOMAIN_CONFIDENCE.items():
        if domain.endswith(k):
            return v
    return 0.6  # 默认普通网站


def content_quality(content: str) -> float:
    """内容结构质量（不涉及语义）"""
    length = len(content)

    if length < 50:
        return 0.2
    if length < 150:
        return 0.5
    if length < 400:
        return 0.8
    return 1.0


def rule_based_score(url: str, content: str) -> float:
    """
    规则可信度评分（0~1）
    不使用关键词，仅使用稳定结构信号
    """
    source_score = source_prior(url)
    quality_score = content_quality(content)

    # 规则部分不主导，只做修正
    score = 0.6 * source_score + 0.4 * quality_score
    return round(min(score, 1.0), 3)


def normalize_results(
        raw_results: List[Dict],
        query: str,
) -> List[WebFact]:
    """
    Web 搜索结果标准化 + 可信度评估

    confidence =
        0.6 * embedding 相似度 +
        0.4 * 规则可信度（来源 + 结构）
    """

    embedder = get_embedding()
    query_embedding = embedder.embed_query(query)

    facts: List[WebFact] = []

    for r in raw_results:
        content = r.get("content") or r.get("snippet")
        url = r.get("url")

        if not content or not url:
            continue

        # ===== 1️⃣ embedding 相似度 =====
        doc_embedding = embedder.embed_documents([content])[0]
        semantic_score = cosine_similarity(query_embedding, doc_embedding)

        # 映射到 0~1（经验区间）
        semantic_score = max(0.0, min((semantic_score - 0.2) / 0.6, 1.0))

        # ===== 2️⃣ 规则可信度 =====
        rule_score = rule_based_score(url, content)

        # ===== 3️⃣ 混合 =====
        confidence = round(
            0.6 * semantic_score + 0.4 * rule_score,
            3
        )

        facts.append(
            WebFact(
                content=content.strip(),
                source=urlparse(url).netloc,
                url=url,
                confidence=confidence,
            )
        )

    facts.sort(key=lambda x: x.confidence, reverse=True)
    return facts
