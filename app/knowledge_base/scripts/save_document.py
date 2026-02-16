import hashlib
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from urllib.parse import urlparse

from app.db.knowledge_model import Document


def save_document(db, soup, url) -> Document:
    # 1️⃣ 生成 doc_id
    doc_id = hashlib.md5(url.encode()).hexdigest()

    # 2️⃣ 如果已经存在就直接返回
    existing = db.query(Document).filter(Document.id == doc_id).first()
    if existing:
        return existing

    # ================================
    # 3️⃣ 解析 URL
    # ================================
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]

    # 例如：
    # ['cat-owners', 'introduction-to-cats', 'physical-description-of-cats']

    # ---------- title ----------
    title = path_parts[-1].replace("-", " ").strip() if len(path_parts) >= 1 else "Untitled"

    # ---------- category ----------
    category = path_parts[-2] if len(path_parts) >= 2 else None

    # ---------- source_version ----------
    source_version = path_parts[-3] if len(path_parts) >= 3 else None

    # ================================
    # 4️⃣ 解析 species
    # ================================
    species = "uncertain"

    if len(path_parts) >= 1:
        first_segment = path_parts[0]

        # 情况 1：cat-owners / dog-owners
        if first_segment.endswith("-owners"):
            species = first_segment.replace("-owners", "")

        # 情况 2：all-other-pets/{species}
        elif first_segment == "all-other-pets" and len(path_parts) >= 2:
            species = path_parts[1]

        # 情况 3：special-pet-topics
        elif first_segment == "special-pet-topics":
            # 在后续路径中寻找常见动物名
            animal_keywords = [
                "dog", "cat", "rabbit", "bird", "ferret",
                "chinchilla", "hamster", "guinea-pig",
                "reptile", "snake", "lizard"
            ]

            species_list = []
            for part in path_parts[1:]:
                for animal in animal_keywords:
                    if animal in part:
                        species_list.append(animal)
            species_list = list(set(species_list))
            if not species_list:
                species_list.append("uncertain")
            species = ",".join(species_list)

    # ================================
    # 5️⃣ 提取作者（支持多个）
    # ================================
    authors = []

    author_blocks = soup.find_all(
        "div",
        class_=lambda x: x and "TopicHead_topic__authors__description" in x
    )

    for block in author_blocks:
        link = block.find("a")
        if link:
            name = link.get_text(strip=True)
            if name:
                authors.append(name)

    authors = list(dict.fromkeys(authors))
    author = ",".join(authors) if authors else None

    # ================================
    # 6️⃣ 创建 Document
    # ================================
    document = Document(
        id=doc_id,
        title=title,
        url=url,
        author=author,
        species=species,
        category=category,
        source_version=source_version,
        source_platform="MSD Manuals",
        created_at=datetime.utcnow()
    )

    try:
        db.add(document)
        db.flush()
        return document

    except IntegrityError:
        db.rollback()
        return db.query(Document).filter(Document.id == doc_id).first()
