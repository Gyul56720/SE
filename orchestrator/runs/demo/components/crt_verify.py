def check(output, inputs):
    N, t = output["N"], output["target"]
    for x in output["solutions"]:
        if (x*x) % N != t % N:
            return False, f"x={x} not a root mod N"
    return (len(output["solutions"]) > 0), "ok"
