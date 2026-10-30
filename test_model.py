"""Run: python test_model.py   (asserts the numbers shown on the slide)"""
import battsimx_model as bm

D = {d["key"]: d for d in bm.DESIGNS}
exp = {"Baseline": 55.0, "Opt A": 46.1, "Opt B": 39.0, "Opt C": 39.6}
for k, t in exp.items():
    r = bm.run(D[k])
    assert abs(r["peak_T"] - t) < 0.05, (k, r["peak_T"], t)
assert not bm.run(D["Baseline"])["T_ok"] and not bm.run(D["Opt A"])["T_ok"]
assert bm.run(D["Opt B"])["T_ok"] and bm.run(D["Opt C"])["T_ok"]
b, o = bm.run(D["Baseline"]), bm.run(D["Opt B"])
assert abs((o["cost_per_kwh"] / b["cost_per_kwh"] - 1) * 100 + 32.4) < 0.1
print("all checks passed")
