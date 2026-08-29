import argparse
import time
from verifier import verify_scheme
from searcher import Searcher
import json
import os

def run_loop(iterations, sleep_time):
    searcher = Searcher(b=3, m=21)
    for i in range(iterations):
        scheme = searcher.propose()
        ok, msg = verify_scheme(scheme)
        searcher.save_log(msg)
        print(f"Iteration {i+1}: {ok}, {msg}")
        time.sleep(sleep_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--sleep", type=int, default=20)
    args = parser.parse_args()
    run_loop(args.iterations, args.sleep)
