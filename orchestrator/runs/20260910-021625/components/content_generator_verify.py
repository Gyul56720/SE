def check(output, inputs):
    content = output.get("content")
    if not content or not isinstance(content, str):
        return False, "content is invalid"
    return True, "success"