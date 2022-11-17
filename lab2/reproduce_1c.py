# This code is part of the Advanced Computer Networks course at Vrije
# Universiteit Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import topo
import plotly.graph_objects as go
from os import getcwd
from dijkstra import Dijkstra

# Same setup for Jellyfish and Fattree
num_servers = 686
num_switches = 245
num_ports = 14

# Fat Tree
ft_path_length_count = dict(zip(range(2, 7), [0] * 5))
ft_topo = topo.Fattree(num_ports)
dijkstra_fattree = Dijkstra(ft_topo.servers, ft_topo.switches)
for i in range(num_servers - 1):
    for j in range(i + 1, num_servers):
        path_length = dijkstra_fattree.get_path_length(
            ft_topo.servers[i], ft_topo.servers[j]
        )
        ft_path_length_count.setdefault(path_length, 0)
        ft_path_length_count[path_length] += 1
del ft_topo
# print(ft_path_length_count)


# Jellyflish
jf_path_length_count = dict(zip(range(2, 7), [0] * 5))
# run 3 time
for _ in range(3):
    jf_topo = topo.Jellyfish(num_servers, num_switches, num_ports)
    dijkstra_jellyfish = Dijkstra(jf_topo.servers, jf_topo.switches)
    for i in range(num_servers - 1):
        for j in range(i + 1, num_servers):
            path_length = dijkstra_jellyfish.get_path_length(
                jf_topo.servers[i], jf_topo.servers[j]
            )
            jf_path_length_count.setdefault(path_length, 0)
            jf_path_length_count[path_length] += 1
    del jf_topo
# print(jf_path_length_count)


x_path_length = [i for i in range(2, 7)]
fig = go.Figure(
    data=[
        go.Bar(
            name="Jellyfish",
            x=x_path_length,
            y=[
                jf_path_length_count[i] / sum(jf_path_length_count.values())
                for i in range(2, 7)
            ],
        ),
        go.Bar(
            name="Fat-tree",
            x=x_path_length,
            y=[
                ft_path_length_count[i] / sum(ft_path_length_count.values())
                for i in range(2, 7)
            ],
        ),
    ]
)
fig.update_layout(
    xaxis={"title": "Path length"},
    yaxis={"title": "Fraction of Server Pairs", "range": [0, 1]},
    title_text="Reproduce Figure 1(c)",
    legend=dict(font=dict(size = 24), yanchor="top", y=0.99, xanchor="left", x=0.01),
)

filename = "reproduce_1c.html"
fig.write_html(filename)
print(f"See output figure in {getcwd()+ '/' +filename}")
fig.show()
