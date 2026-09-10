def check(output, inputs):
    if not isinstance(output, dict):
        return False, "output must be a dict"
    if "accommodation" not in output or "route_info" not in output or "itinerary_items" not in output:
        return False, "missing required keys"
    if len(output["itinerary_items"]) == 0:
        return False, "itinerary items cannot be empty"
    return True, "success"