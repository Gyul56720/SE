def check(output, inputs):
    if "schedule" not in output:
        return False, "schedule key missing"
    schedule = output["schedule"]
    if len(schedule) != 4:
        return False, "itinerary must span 4 days"
    dates = [s["date"] for s in schedule]
    expected_dates = ["2026-09-13", "2026-09-14", "2026-09-15", "2026-09-16"]
    if dates != expected_dates:
        return False, "date sequence mismatch"
    return True, "success"