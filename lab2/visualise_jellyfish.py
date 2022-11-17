import topo
import plotly.graph_objects as go
import random
from os import getcwd
from dijkstra import Dijkstra


print("=====Genrate Jellyfish topology and visualize=====")
num_servers = 686
num_switches = 245
num_ports = 14

num_servers = int(input(f"Input the number of server (default {num_servers} servers): "))
num_switches = int(input(f"Input the number of switch (default {num_switches} switchs): "))
num_ports = int(input(f"Input the number of port (default {num_ports} ports): "))

room_width = round(num_switches**0.5 + 0.5)
room_length = round(num_switches / room_width + 0.5)
# generate random position

# Jellyfish
jf_topo = topo.Jellyfish(num_servers, num_switches, num_ports)

# assign position for every switch
switch_position = {}
switch_count = 0
for x in range(room_width):
    for y in range(room_length):
        switch = jf_topo.stable_switches[switch_count]
        switch_position[switch.id] = (x, y)
        switch_count += 1
        if switch_count == num_switches:
            break
# print(switch_position)
# figure init
fig = go.Figure()

show_legend_flag = {"switch": True, "host": True}
for switch_count in range(num_switches):
    switch = jf_topo.switches[switch_count]
    for edge in switch.edges:
        if edge.rnode.id == switch.id:
            s1 = switch
            s2 = edge.lnode
        else:
            s1 = switch
            s2 = edge.rnode
        if s2.type == "switch":
            x = [switch_position[s1.id][0], switch_position[s2.id][0]]
            y = [switch_position[s1.id][1], switch_position[s2.id][1]]
            z = [1, 1]
            _ = fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="markers+lines",
                    name="switches",
                    line={"color": "gray"},
                    legendgroup="switches",
                    showlegend=show_legend_flag[s2.type],
                )
            )
        elif s2.type == "host":
            x = [switch_position[s1.id][0], switch_position[s1.id][0] + random.randint(3,8)/10]
            y = [switch_position[s1.id][1], switch_position[s1.id][1] + random.randint(3,8)/10]
            # z = [1, (s2.id - s1.id) * -1]
            z = [1, 0]
            # print(s1.id, s2.id)
            _ = fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="markers+lines",
                    name="hosts",
                    line={"color": "orange"},
                    legendgroup="hosts",
                    showlegend=show_legend_flag[s2.type],
                )
            )
            _ = fig.add_trace(
                go.Scatter3d(
                    x = [switch_position[s1.id][0]],
                    y = [switch_position[s1.id][1]],
                    z=[1],
                    mode="markers",
                    name="switches",
                    line={"color": "gray"},
                    legendgroup="switches",
                    showlegend=False,
                )
            )
        show_legend_flag[s2.type] = False

fig.update_layout(
    title_text=f"Jellyfish Topology: #server = {num_servers}, #switch = {num_switches}, #port = {num_ports}",
    legend=dict(font=dict(size = 24), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

filename = f"jellyfish_k{num_ports}.html"
fig.write_html(filename)
print(f"See output topology in {getcwd()+ '/' +filename}")
fig.show()