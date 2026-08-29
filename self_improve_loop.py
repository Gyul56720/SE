from mathmetics.matrix_exponent.verifier import verify_scheme
from searcher import Searcher
import json
import os

def run_loop(iterations=3):
    searcher = Searcher(b=3, m=21)
    
    for i in range(iterations):
        print(f"Iteration {i+1}...")
        scheme = searcher.propose()
        
        ok, msg = verify_scheme(scheme)
        print(f"Result: {ok}, Message: {msg}")
        
        searcher.save_log(scheme, msg)
        
    print("Loop finished. Check logs/history.jsonl")

if __name__ == "__main__":
    run_loop()
