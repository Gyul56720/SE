def check(output, inputs):
    if "framework_name" not in output:
        return False, "Framework proposal incomplete."
    return True, "Framework proposal structurally valid."