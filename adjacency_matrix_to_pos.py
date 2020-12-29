import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


def get_position(width, height, _aj_matrix: np.array):
    # aj_matrix = np.array([
    #     [0, 1, 0, 1, 0, 1, 0],  # 0
    #     [0, 0, 0, 1, 1, 1, 0],  # 1
    #     [0, 1, 0, 1, 0, 1, 0],  # 2
    #     [0, 0, 0, 0, 1, 1, 0],  # 3
    #     [0, 1, 0, 1, 0, 1, 0],  # 4
    #     [0, 1, 0, 1, 1, 0, 0],  # 5
    #     [0, 1, 0, 1, 1, 0, 0],  # 6
    # ])

    _edge_list = []
    for i in range(len(_aj_matrix)):
        for j in range(len(_aj_matrix[i])):
            if _aj_matrix[i][j] != 0:
                _edge_list.append((i, j))

    G = nx.Graph(_edge_list)
    position = nx.kamada_kawai_layout(G)
    # 无法画出孤立点
    # nx.draw_networkx_nodes(G, position, nodelist=np.arange(len(aj_matrix)))
    # nx.draw_networkx_edges(G, position)
    # nx.draw_networkx_labels(G, position)
    # plt.show()
    # print(position)
    trans_position = dict()
    for _id, _pos in position.items():
        # 加40px的偏置，防止画到边界外
        trans_position[_id] = (round(abs((_pos[0] + 1) * width / 2) + 40), round(abs((_pos[1] - 1) * height / 2)) + 40)

    return trans_position, _edge_list


if __name__ == '__main__':
    aj_matrix = np.array([
        [0, 1, 0, 1, 0, 1, 0],  # 0
        [0, 0, 0, 1, 1, 1, 0],  # 1
        [0, 1, 0, 1, 0, 1, 0],  # 2
        [0, 0, 0, 0, 1, 1, 0],  # 3
        [0, 1, 0, 1, 0, 1, 0],  # 4
        [0, 1, 0, 1, 1, 0, 0],  # 5
        [0, 1, 0, 1, 1, 0, 0],  # 6
    ])
    position_dict, edge_list = get_position(400, 400, aj_matrix)
    print(position_dict)
    print(edge_list)
