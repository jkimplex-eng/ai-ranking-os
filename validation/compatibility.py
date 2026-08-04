from typing import Any


def build_compatibility_matrix(stages: dict[str, Any]) -> list[dict[str, Any]]:
    executor = stages["executor"]
    extraction = stages["entity_extraction"]
    matrix = [
        {
            "producer": "Query",
            "consumer": "Intent",
            "status": "PASS" if stages["query"]["query"] else "FAIL",
            "contract": "query:string",
        },
        {
            "producer": "Intent",
            "consumer": "Router",
            "status": (
                "PASS"
                if stages["intent"]["primary_intent"]
                and stages["router"]["request_id"] == stages["correlation_id"]
                else "FAIL"
            ),
            "contract": "IntentResult→ExecutionPlan",
        },
        {
            "producer": "Router",
            "consumer": "Executor",
            "status": (
                "PASS"
                if stages["router"]["plan_id"] == executor["plan_id"]
                else "FAIL"
            ),
            "contract": "ExecutionPlan v1",
        },
        {
            "producer": "Executor",
            "consumer": "Entity Extraction",
            "status": "PASS" if executor["output"] is not None else "FAIL",
            "contract": "provider output→raw_response",
        },
        {
            "producer": "Entity Extraction",
            "consumer": "Reason Engine",
            "status": (
                "PASS"
                if stages["reason"]["entity_count"] == len(extraction["entities"])
                else "FAIL"
            ),
            "contract": "ExtractionResult→ReasonContext",
        },
        {
            "producer": "Reason Engine",
            "consumer": "Visibility Engine",
            "status": (
                "PASS"
                if stages["visibility"]["entity"] == stages["reason"]["subject"]
                else "FAIL"
            ),
            "contract": "ReasonContext→VisibilityInput",
        },
        {
            "producer": "Entity Extraction",
            "consumer": "Knowledge Graph",
            "status": (
                "PASS"
                if len(stages["knowledge_graph"]["nodes"]) == len(extraction["entities"])
                else "FAIL"
            ),
            "contract": "entities/relations→nodes/edges",
        },
        {
            "producer": "Knowledge Graph",
            "consumer": "Response",
            "status": (
                "PASS"
                if stages["response"]["correlation_id"] == stages["correlation_id"]
                else "FAIL"
            ),
            "contract": "PipelineResponse v1",
        },
    ]
    return matrix


def compatibility_passed(matrix: list[dict[str, Any]]) -> bool:
    return all(row["status"] == "PASS" for row in matrix)

