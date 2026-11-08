import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from preview import Chart, sheet
pkg, out = sys.argv[1], sys.argv[2]
beats = [float(x) for x in sys.argv[3].split(",")]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 4
W = int(sys.argv[5]) if len(sys.argv) > 5 else 480
ch = Chart(pkg)
times = [b * ch.spb for b in beats]
sheet(ch, times, out, cols, W, labels=[f"beat {b:.2f} bar {(b-2)/4:.1f}" for b in beats])
print("saved", out)
