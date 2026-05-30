"""
图算法模块

提供常用的图分析算法
"""

import networkx as nx
from typing import Optional
from models import Entity, EntityType
from graph_store import GraphStore


class GraphAlgorithms:
    """
    图算法集合

    支持:
    1. 中心性分析: 度中心性、介数中心性、接近中心性
    2. 社区发现: Louvain 算法
    3. 路径分析: 最短路径、所有路径
    4. 图统计: 度分布、连通分量
    """

    def __init__(self, graph_store: GraphStore):
        """
        初始化

        参数:
            graph_store: 图谱存储实例
        """
        self.store = graph_store
        self.graph = graph_store.graph

    # ==================== 中心性分析 ====================

    def degree_centrality(self, top_k: int = 10) -> list[dict]:
        """
        度中心性分析

        度中心性 = 节点的度数 / (n-1)
        值越高表示该节点连接越多
        """
        if self.graph.number_of_nodes() == 0:
            return []

        centrality = nx.degree_centrality(self.graph)

        # 排序
        sorted_items = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            {"name": name, "centrality": round(score, 4)}
            for name, score in sorted_items
        ]

    def betweenness_centrality(self, top_k: int = 10) -> list[dict]:
        """
        介数中心性分析

        介数中心性 = 经过该节点的最短路径比例
        值越高表示该节点是重要的"桥梁"
        """
        if self.graph.number_of_nodes() == 0:
            return []

        centrality = nx.betweenness_centrality(self.graph)

        sorted_items = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            {"name": name, "centrality": round(score, 4)}
            for name, score in sorted_items
        ]

    def closeness_centrality(self, top_k: int = 10) -> list[dict]:
        """
        接近中心性分析

        接近中心性 = 1 / 到其他所有节点的平均距离
        值越高表示该节点越"中心"
        """
        if self.graph.number_of_nodes() == 0:
            return []

        centrality = nx.closeness_centrality(self.graph)

        sorted_items = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            {"name": name, "centrality": round(score, 4)}
            for name, score in sorted_items
        ]

    def pagerank(self, top_k: int = 10) -> list[dict]:
        """
        PageRank 算法

        衡量节点的重要性
        """
        if self.graph.number_of_nodes() == 0:
            return []

        try:
            pr = nx.pagerank(self.graph)
        except:
            return []

        sorted_items = sorted(
            pr.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            {"name": name, "score": round(score, 4)}
            for name, score in sorted_items
        ]

    # ==================== 社区发现 ====================

    def detect_communities(self) -> dict:
        """
        社区发现 (Louvain 算法)

        将图分成若干社区，社区内连接紧密，社区间连接稀疏
        """
        if self.graph.number_of_nodes() == 0:
            return {"communities": [], "modularity": 0}

        # 转换为无向图
        undirected = self.graph.to_undirected()

        try:
            # 使用 Louvain 算法
            from community import community_louvain
            partition = community_louvain.best_partition(undirected)
            modularity = community_louvain.modularity(partition, undirected)
        except ImportError:
            # 如果没有 python-louvain，使用 networkx 的方法
            try:
                communities = list(nx.community.greedy_modularity_communities(undirected))
                partition = {}
                for i, comm in enumerate(communities):
                    for node in comm:
                        partition[node] = i
                modularity = nx.community.modularity(undirected, communities)
            except:
                return {"communities": [], "modularity": 0, "error": "No community detection available"}

        # 整理结果
        community_map = {}
        for node, comm_id in partition.items():
            if comm_id not in community_map:
                community_map[comm_id] = []
            community_map[comm_id].append(node)

        communities = [
            {
                "id": comm_id,
                "nodes": nodes,
                "size": len(nodes),
            }
            for comm_id, nodes in community_map.items()
        ]

        # 按大小排序
        communities.sort(key=lambda x: x["size"], reverse=True)

        return {
            "communities": communities,
            "modularity": round(modularity, 4),
            "community_count": len(communities),
        }

    # ==================== 路径分析 ====================

    def shortest_path(self, source: str, target: str) -> Optional[dict]:
        """
        最短路径

        返回:
            路径信息或 None
        """
        if source not in self.graph or target not in self.graph:
            return None

        try:
            path = nx.shortest_path(self.graph, source, target)
            length = nx.shortest_path_length(self.graph, source, target)

            return {
                "path": path,
                "length": length,
                "edges": [
                    {
                        "source": path[i],
                        "target": path[i + 1],
                        "relation": self.graph.edges[path[i], path[i + 1]].get(
                            "relation_type", "related_to"
                        ),
                    }
                    for i in range(len(path) - 1)
                ],
            }
        except nx.NetworkXNoPath:
            return None

    def all_simple_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """
        所有简单路径

        返回:
            路径列表
        """
        if source not in self.graph or target not in self.graph:
            return []

        try:
            paths = list(nx.all_simple_paths(
                self.graph, source, target, cutoff=max_depth
            ))
            return paths[:20]  # 最多返回 20 条
        except:
            return []

    # ==================== 图统计 ====================

    def graph_density(self) -> float:
        """图密度"""
        if self.graph.number_of_nodes() < 2:
            return 0.0
        return round(nx.density(self.graph), 4)

    def connected_components(self) -> list[list[str]]:
        """连通分量"""
        undirected = self.graph.to_undirected()
        components = list(nx.connected_components(undirected))
        return [list(comp) for comp in components]

    def degree_distribution(self) -> dict:
        """度分布"""
        degrees = dict(self.graph.degree())
        if not degrees:
            return {"min": 0, "max": 0, "avg": 0, "distribution": {}}

        values = list(degrees.values())
        distribution = {}
        for d in values:
            distribution[d] = distribution.get(d, 0) + 1

        return {
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 2),
            "distribution": distribution,
        }

    def get_important_nodes(self, top_k: int = 10) -> list[dict]:
        """
        综合评估重要节点

        结合多种中心性指标
        """
        if self.graph.number_of_nodes() == 0:
            return []

        # 计算各种中心性
        degree = nx.degree_centrality(self.graph)

        try:
            betweenness = nx.betweenness_centrality(self.graph)
        except:
            betweenness = {}

        try:
            closeness = nx.closeness_centrality(self.graph)
        except:
            closeness = {}

        # 综合评分
        scores = {}
        for node in self.graph.nodes():
            d = degree.get(node, 0)
            b = betweenness.get(node, 0)
            c = closeness.get(node, 0)
            # 加权平均
            scores[node] = 0.4 * d + 0.3 * b + 0.3 * c

        sorted_items = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            {
                "name": name,
                "score": round(score, 4),
                "degree": round(degree.get(name, 0), 4),
                "betweenness": round(betweenness.get(name, 0), 4),
                "closeness": round(closeness.get(name, 0), 4),
            }
            for name, score in sorted_items
        ]
