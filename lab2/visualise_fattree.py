import plotly.graph_objects as go
import topo
from os import getcwd


print("=====Genrate Fat-Tree topology and visualize=====")
num_ports = 14
num_ports = int(input(f"Input the number of port (default {num_ports} ports): "))

# Fat Tree
ft_topo = topo.Fattree(num_ports)

core_switch = []
pod_switch = []
for switch in ft_topo.switches:
    if switch.type == "core_switch":
        core_switch.append(switch)
    elif switch.type == "pod_switch":
        pod_switch.append(switch)

# figure init
fig = go.Figure()

show_legend_flag = {"pod_switch": True, "core_switch": True, "host": True}
for switch in pod_switch:
    pod_id = int(switch.id.split(".")[1])
    # upper layer
    for edge in switch.edges:
        if edge.rnode.id == switch.id:
            s1 = switch
            s2 = edge.lnode
        else:
            s1 = switch
            s2 = edge.rnode
        # only draw when s1 is upper switch
        if s2.type == "pod_switch":
            s1_id = int(s1.id.split(".")[2])
            s2_id = int(s2.id.split(".")[2])
            if s1_id >= ft_topo.k / 2:
                # upper layer is 2, lawer layer is 1
                z = [2, 1]
                y = [ft_topo.k / 4 + 0.5, ft_topo.k / 4 + 0.5]
                # every pod is pod_id*k/2
                x = [
                    s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2,
                    s2_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2,
                ]
                _ = fig.add_trace(
                    go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        mode="lines+markers",
                        name="pod switches",
                        line={"color": "gray"},
                        legendgroup="pod switches",
                        showlegend=show_legend_flag[s2.type],
                    )
                )
        # connect lower layer to host
        elif s2.type == "host":
            s1_id = int(s1.id.split(".")[2])
            # host id start at 2, at equally
            s2_id = int(s2.id.split(".")[3]) - 2 - (ft_topo.k / 4)
            z = [1, 0]
            y = [ft_topo.k / 4 + 0.5, ft_topo.k / 4 + 0.5]
            x = [
                s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2,
                s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2 + s2_id / 10,
            ]
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
                    x=[s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2],
                    y=[ft_topo.k / 4 + 0.5],
                    z=[1],
                    mode="markers",
                    name="hosts",
                    line={"color": "gray"},
                    legendgroup="hosts",
                    showlegend=False,
                )
            )
        elif s2.type == "core_switch":
            s1_id = int(s1.id.split(".")[2])
            s2_id_row = int(s2.id.split(".")[2])
            s2_id_col = int(s2.id.split(".")[3])
            z = [2, 3]
            y = [
                ft_topo.k / 4 + 0.5,
                s2_id_row
                # s2_id_row * ft_topo.k + pod_id * ft_topo.k / 2
            ]
            x = [
                s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2,
                s2_id_col * ft_topo.k / 2 + (ft_topo.k / 2) ** 2 / 2
                # s2_id_col * ft_topo.k,
            ]
            _ = fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="markers+lines",
                    name="core switches",
                    line={"color": "darkred"},
                    legendgroup="core switches",
                    showlegend=show_legend_flag[s2.type],
                )
            )
            _ = fig.add_trace(
                go.Scatter3d(
                    x=[s1_id % (ft_topo.k / 2) + pod_id * ft_topo.k / 2],
                    y=[ft_topo.k / 4 + 0.5],
                    z=[2],
                    mode="markers",
                    name="hosts",
                    line={"color": "gray"},
                    legendgroup="hosts",
                    showlegend=False,
                )
            )
        show_legend_flag[s2.type] = False


fig.update_layout(
    title_text=f"Fat-Tree Topology, k = {num_ports}",
    legend=dict(font=dict(size = 24), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

filename = f"fattree_k{num_ports}.html"
fig.write_html(filename)
print(f"See output topology in {getcwd()+ '/' +filename}")
fig.show()
