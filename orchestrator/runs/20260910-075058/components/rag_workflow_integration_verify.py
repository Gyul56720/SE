def check(output, inputs):
    if len(output) != 3:
        return False, "Expected 3 workflow strategies."
    if not all("Query VectorDB" in val for val in output.values()):
        return False, "Workflows must explicitly involve RAG vector retrieval."
    return True, "Workflow strategies verified."