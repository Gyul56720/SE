def check(output, inputs):
    # Ensure report contains actionable SCAL resolution content
    if "final_report" in output and "SCAL" in output["final_report"]:
        return True, "Report validated"
    return False, "Report lacks SCAL context"