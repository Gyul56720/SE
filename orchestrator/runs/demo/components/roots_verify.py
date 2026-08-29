def check(output, inputs):
    for x in output["rp"]:
        if (x*x) % output["p"] != output["target"] % output["p"]:
            return False, "bad root mod p"
    if not output["rp"] or not output["rq"]:
        return False, "no roots"
    return True, "ok"
