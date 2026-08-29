from verifier import verify_scheme
from searcher import Searcher
import json

def run_loop(iterations=3):
    searcher = Searcher(b=3, m=21)
    for i in range(iterations):
        scheme = searcher.propose()
        ok, msg = verify_scheme(scheme)
        searcher.save_log(msg)
        print(f"Iteration {i+1}: {ok}, {msg}")

if __name__ == "__main__":
    run_loop()
