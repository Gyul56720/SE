def check(output, inputs):
    if output["p"]*output["q"] != output["N"]:
        return False, "p*q != N"
    if output["p"] in (1, output["N"]):
        return False, "trivial factor"
    return True, "ok"
