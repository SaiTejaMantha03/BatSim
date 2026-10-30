"""
BattSimulator web interface (Flask). Runs the SAME model as battsimx_model.py.

  pip install flask
  python app.py          then open http://127.0.0.1:5000

Pick a cell, S x P layout, cooling and load; the page recomputes peak cell temperature,
energy, mass and cost per kWh, and flags any design above 45 C or over the cell current rating.
"""
from flask import Flask, jsonify, request, render_template_string
import battsimx_model as bm

app = Flask(__name__)
CELLS = {"NMC": bm.NMC, "LFP": bm.LFP}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>BattSimulator</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--navy:#0B2E4F;--blue:#00A0E0;--bg:#F4FAFD;--line:#C9E6F6;--ok:#1C8C3C;--bad:#C62828}
*{box-sizing:border-box}body{margin:0;font-family:Calibri,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--navy)}
header{background:var(--navy);color:#fff;padding:14px 24px;display:flex;align-items:baseline;gap:14px}
header h1{margin:0;font-size:26px}header h1 span{color:#8FD8F8}header small{color:#8FD8F8;font-size:14px}
main{max-width:1100px;margin:0 auto;padding:18px 24px}
.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:10px;background:#fff;border:2px solid var(--blue);border-radius:12px;padding:14px}
label{display:block;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#0077B6;margin-bottom:4px}
select,input{width:100%;font-size:16px;padding:7px 8px;border:1px solid var(--line);border-radius:6px;color:var(--navy);background:#fff}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}
.tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.tile .k{font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#0077B6}
.tile .v{font-size:34px;font-weight:700;line-height:1.15}.tile .s{font-size:13px;color:#26384D}
.verdict{border-width:3px}.pass{border-color:var(--ok)}.pass .v{color:var(--ok)}.fail{border-color:var(--bad)}.fail .v{color:var(--bad)}
.flags{margin:14px 0 0;padding:0;list-style:none;font-size:15px}.flags li{margin:4px 0}.flags .w{color:var(--bad);font-weight:700}
table{width:100%;border-collapse:collapse;margin-top:18px;background:#fff;border:1px solid var(--line);font-size:15px}
th{background:var(--navy);color:#fff;text-align:left;padding:8px}td{padding:7px 8px;border-top:1px solid var(--line)}
h2{font-size:15px;letter-spacing:.04em;text-transform:uppercase;color:#0077B6;margin:22px 0 0}
.note{font-size:13px;color:#26384D;margin-top:14px}
</style></head><body>
<header><h1>Batt<span>Simulator</span></h1><small>Virtual design platform for battery energy systems</small></header>
<main>
<div class="controls">
 <div><label>Cell</label><select id="cell"><option value="NMC">NMC 21700 (Samsung 50E)</option><option value="LFP">LFP 32700</option></select></div>
 <div><label>Series (S)</label><input id="Ns" type="number" min="1" max="30" value="14"></div>
 <div><label>Parallel (P)</label><input id="Np" type="number" min="1" max="12" value="4"></div>
 <div><label>Cooling</label><select id="cooling"><option value="air">Natural air</option><option value="forced">Forced air</option><option value="pcm">PCM</option></select></div>
 <div><label>Load (W)</label><input id="load" type="number" min="100" max="5000" step="100" value="1000"></div>
 <div><label>Ambient (°C)</label><input id="amb" type="number" min="-20" max="55" value="35"></div>
 <div><label>PCM size (× cell heat)</label><input id="pcmf" type="number" min="0.25" max="4" step="0.25" value="2"></div>
</div>
<div class="tiles" id="tiles"></div>
<ul class="flags" id="flags"></ul>
<h2>Preset comparison (1 kW, 35 °C)</h2>
<table id="cmp"><thead><tr><th>Design</th><th>Peak T</th><th>Energy</th><th>Wh/kg</th><th>Mass</th><th>$/kWh</th><th>Verdict</th></tr></thead><tbody></tbody></table>
<p class="note">Lumped electro-thermal model, calibrated on the Panasonic 18650PF drive-cycle data and checked on unseen −20 °C cycles. Natural-air heat transfer, PCM properties and the LFP cell mass are assumptions (see README).</p>
</main>
<script>
const $=id=>document.getElementById(id);
function q(extra){const p=new URLSearchParams({cell:$('cell').value,Ns:$('Ns').value,Np:$('Np').value,cooling:$('cooling').value,load:$('load').value,amb:$('amb').value,pcmf:$('pcmf').value});return p.toString()}
function tile(k,v,s,cls=''){return `<div class="tile ${cls}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`}
async function run(){
 const r=await (await fetch('/api/run?'+q())).json(); if(r.error){$('tiles').innerHTML=tile('Error',':(',r.error,'fail');return}
 const ok=r.T_ok&&r.I_ok;
 $('tiles').innerHTML=tile('Peak cell temp',r.peak_T.toFixed(1)+' °C','limit 45 °C',r.T_ok?'':'fail')
  +tile('Verdict',ok?'PASS':'FAIL',ok?'within limits':'see flags below','verdict '+(ok?'pass':'fail'))
  +tile('Energy',(r.E_wh/1000).toFixed(2)+' kWh',r.hours.toFixed(2)+' h at '+$('load').value+' W')
  +tile('Mass',r.mass.toFixed(1)+' kg',r.wh_per_kg.toFixed(0)+' Wh/kg')
  +tile('Cost per kWh','$'+r.cost_per_kwh.toFixed(0),'per delivered kWh')
  +tile('Cell current',r.I_cell.toFixed(1)+' A',r.c_rate.toFixed(2)+' C'+(r.I_ok?'':' (over rating)'));
 const f=[];f.push(r.T_ok?'<li>Temperature within the 45 °C limit.</li>':'<li class="w">Peak temperature above the 45 °C limit.</li>');
 f.push(r.I_ok?'<li>Cell current within its rating.</li>':'<li class="w">Cell current above its rating.</li>');
 f.push(`<li>Pack: ${r.cells} cells, ${r.Vnom.toFixed(1)} V nominal${r.pcm_kg>0?', PCM '+r.pcm_kg.toFixed(2)+' kg':''}.</li>`);
 $('flags').innerHTML=f.join('');
}
async function cmp(){
 const rows=await (await fetch('/api/presets')).json();
 $('cmp').querySelector('tbody').innerHTML=rows.map(r=>`<tr><td>${r.label}</td><td>${r.peak_T.toFixed(1)} °C</td><td>${(r.E_wh/1000).toFixed(2)} kWh</td><td>${r.wh_per_kg.toFixed(0)}</td><td>${r.mass.toFixed(1)} kg</td><td>${r.cost_per_kwh.toFixed(0)}</td><td style="font-weight:700;color:${r.verdict=='PASS'?'#1C8C3C':'#C62828'}">${r.verdict}</td></tr>`).join('');
}
document.querySelectorAll('select,input').forEach(e=>e.addEventListener('input',run));
run();cmp();
</script></body></html>"""


def _run(args):
    cell = CELLS[args.get("cell", "NMC")]
    design = dict(cell=cell, Ns=int(args.get("Ns", 14)), Np=int(args.get("Np", 4)),
                  cooling=args.get("cooling", "air"), label="custom")
    p = dict(bm.DEFAULT)
    p.update(pcm_factor=float(args.get("pcmf", 2)), load=float(args.get("load", 1000)),
             amb=float(args.get("amb", 35)))
    return bm.run(design, p)          # load/ambient passed per call: safe with threaded requests


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/run")
def api_run():
    try:
        return jsonify(_run(request.args))
    except Exception as e:                      # bad input, e.g. load too high for the cells
        return jsonify(error=str(e))


@app.route("/api/presets")
def api_presets():
    out = []
    for d in bm.DESIGNS:
        r = bm.run(d); r["verdict"] = "PASS" if (r["T_ok"] and r["I_ok"]) else "FAIL"; out.append(r)
    return jsonify(out)


if __name__ == "__main__":
    app.run(debug=False)
