from place import place_rtl
res = place_rtl("simple_counter.v", top="simple_counter", target_mhz=50.0, chip="hx8k")
print(res)
