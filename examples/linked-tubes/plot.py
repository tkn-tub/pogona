#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt


df = pd.read_csv("sensor_data/sensor[sensor].csv")
fig, ax = plt.subplots(figsize=(6, 3.5))
df.plot(x='sim_time', y='rel_susceptibility', ax=ax, legend=False)
ax.set_xlabel("Time in s")
ax.set_ylabel("Scaled susceptibility")
fig.tight_layout(pad=.3)
fig.savefig("plot.png", dpi=300)
