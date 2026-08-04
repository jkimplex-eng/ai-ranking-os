from query_intent.schemas import ExpectedOutput, IntentType

OUTPUTS: dict[IntentType, ExpectedOutput] = {
    IntentType.INFORMATIONAL: ExpectedOutput(
        format="ANSWER", fields=["answer", "sources"], cardinality="SINGLE"
    ),
    IntentType.NAVIGATIONAL: ExpectedOutput(
        format="LINK", fields=["title", "url"], cardinality="SINGLE"
    ),
    IntentType.TRANSACTIONAL: ExpectedOutput(
        format="ACTION", fields=["provider", "action_url", "price"], cardinality="ONE_OR_MORE"
    ),
    IntentType.COMMERCIAL_INVESTIGATION: ExpectedOutput(
        format="PRODUCT_ANALYSIS",
        fields=["product", "features", "price", "reviews"],
        cardinality="ONE_OR_MORE",
    ),
    IntentType.COMPARISON: ExpectedOutput(
        format="COMPARISON_TABLE",
        fields=["option", "pros", "cons", "differences"],
        cardinality="MULTIPLE",
    ),
    IntentType.RECOMMENDATION: ExpectedOutput(
        format="RANKED_LIST",
        fields=["rank", "item", "reason"],
        cardinality="MULTIPLE",
    ),
    IntentType.TROUBLESHOOTING: ExpectedOutput(
        format="DIAGNOSTIC",
        fields=["cause", "fix", "verification"],
        cardinality="ONE_OR_MORE",
    ),
    IntentType.HOW_TO: ExpectedOutput(
        format="STEP_BY_STEP",
        fields=["step", "instruction", "expected_result"],
        cardinality="MULTIPLE",
    ),
    IntentType.LOCAL: ExpectedOutput(
        format="LOCAL_RESULTS",
        fields=["name", "address", "distance", "rating"],
        cardinality="MULTIPLE",
    ),
    IntentType.RESEARCH: ExpectedOutput(
        format="RESEARCH_REPORT",
        fields=["summary", "evidence", "methodology", "sources"],
        cardinality="SINGLE",
    ),
}


def expected_output_for(intent: IntentType) -> ExpectedOutput:
    return OUTPUTS[intent].model_copy(deep=True)

