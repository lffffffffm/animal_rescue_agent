from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from app.agent.state import AgentState
from app.agent.prompts import LOW_CONFIDENCE_GENERATE_PROMPT
from app.llm import get_llm


def low_confidence_generate(state: AgentState) -> AgentState:
    """
    低可信生成节点：
    在证据不足或可信度偏低时，生成带不确定性声明的回答
    """

    llm = get_llm().llm

    query = state.get("query")
    merged_docs = state.get("merged_docs", [])

    logger.warning(
        f"LowConfidenceGenerate：证据不足，docs={len(merged_docs)}"
    )

    # ① 构造 evidence 文本（非常重要）
    evidence_blocks = []
    for i, doc in enumerate(merged_docs, 1):
        source = doc.get("source", "unknown")
        content = doc.get("content", "")
        confidence = doc.get("confidence")

        if confidence is not None:
            evidence_blocks.append(
                f"[{i}] 来源: {source} | 可信度: {confidence}\n{content}"
            )
        else:
            evidence_blocks.append(
                f"[{i}] 来源: {source}\n{content}"
            )

    evidence_text = "\n\n".join(evidence_blocks)

    # ② 构建 prompt
    prompt = PromptTemplate(
        template=LOW_CONFIDENCE_GENERATE_PROMPT,
        input_variables=["query", "evidence"],
    )

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "query": query,
        "evidence": evidence_text,
    })

    logger.info("LowConfidenceGenerate：生成完成")

    return {
        **state,
        "response": answer,
        "answer_confidence": "low",
    }
