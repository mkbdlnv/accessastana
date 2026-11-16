"""Pedestrian graph and shortest-path primitives (scipy.sparse.csgraph).

Why scipy instead of pandana: pandana has no wheels for current Python on
Apple Silicon and needs a C++ toolchain. Our city graph (~56k nodes, ~84k
edges) is small enough that scipy's C implementation of Dijkstra runs from
ALL facilities of a category at once in well under a second, using the
"multi-source with offsets" trick below.

Units: coordinates in the city's metric CRS (metres); weights in metres.
Walking time is applied later (distance / speed), so ONE shortest-path run
serves every season profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

# Explicit zero-weight entries may be dropped by scipy sparse matrices, so
# zero-length edges/offsets get a tiny positive weight instead.
EPS = 1e-3


@dataclass
class WalkGraph:
    node_ids: np.ndarray  # (n,) original OSM ids
    xy: np.ndarray  # (n, 2) metric coordinates
    matrix: csr_matrix  # (n, n) symmetric, metres
    _tree: cKDTree = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._tree = cKDTree(self.xy)

    @property
    def n(self) -> int:
        return int(self.node_ids.shape[0])

    @classmethod
    def from_tables(cls, nodes: pd.DataFrame, edges: pd.DataFrame) -> WalkGraph:
        """nodes: id, x, y (metric). edges: u, v, length_m (undirected)."""
        nodes = nodes.reset_index(drop=True)
        index = pd.Series(np.arange(len(nodes)), index=nodes["id"].to_numpy())
        e = edges[edges["u"].isin(index.index) & edges["v"].isin(index.index)]
        a = index.loc[e["u"].to_numpy()].to_numpy()
        b = index.loc[e["v"].to_numpy()].to_numpy()
        w = np.maximum(e["length_m"].to_numpy(dtype=float), EPS)
        # Parallel edges: keep the SHORTEST (a plain COO→CSR conversion would SUM them).
        df = pd.DataFrame({"a": np.minimum(a, b), "b": np.maximum(a, b), "w": w})
        df = df[df.a != df.b].groupby(["a", "b"], as_index=False)["w"].min()
        rows = np.concatenate([df.a, df.b])
        cols = np.concatenate([df.b, df.a])
        data = np.concatenate([df.w, df.w])
        n = len(nodes)
        m = csr_matrix((data, (rows, cols)), shape=(n, n))
        return cls(nodes["id"].to_numpy(), nodes[["x", "y"]].to_numpy(dtype=float), m)

    def snap(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Nearest graph node for each point → (node index, straight-line metres)."""
        if len(xy) == 0:
            return np.empty(0, dtype=int), np.empty(0)
        d, i = self._tree.query(np.asarray(xy, dtype=float))
        return i.astype(int), d

    def multi_source(
        self, source_nodes: np.ndarray, source_offsets: np.ndarray, limit: float = np.inf
    ) -> tuple[np.ndarray, np.ndarray]:
        """Distance from the NEAREST source to every node, and which source it is.

        Trick: add one virtual node per source, connected by a one-way edge
        (virtual → snapped node) whose weight is that source's snap distance.
        A single Dijkstra from all virtual nodes with `min_only=True` then gives
        min over sources of (offset + network distance), i.e. exactly the
        nearest-facility problem. It is O(E log V) once, instead of once per
        facility.

        Returns (dist[n], source_idx[n]); unreachable → (inf, -1).
        """
        k = len(source_nodes)
        if k == 0:
            return np.full(self.n, np.inf), np.full(self.n, -1)
        n = self.n
        coo = self.matrix.tocoo()
        rows = np.concatenate([coo.row, np.arange(n, n + k)])
        cols = np.concatenate([coo.col, np.asarray(source_nodes)])
        data = np.concatenate([coo.data, np.maximum(np.asarray(source_offsets, dtype=float), EPS)])
        aug = csr_matrix((data, (rows, cols)), shape=(n + k, n + k))
        dist, _pred, sources = dijkstra(
            aug,
            directed=True,
            indices=np.arange(n, n + k),
            min_only=True,
            limit=limit,
            return_predecessors=True,
        )
        src = np.where(sources[:n] >= 0, sources[:n] - n, -1)
        return dist[:n], src

    def distances_from(
        self, nodes: np.ndarray, targets: np.ndarray, limit: float = np.inf, chunk: int = 64
    ) -> np.ndarray:
        """Dense (len(nodes), len(targets)) network distances, computed in chunks
        to bound memory (each Dijkstra row is n floats)."""
        out = np.empty((len(nodes), len(targets)))
        for i in range(0, len(nodes), chunk):
            d = dijkstra(self.matrix, directed=False, indices=nodes[i : i + chunk], limit=limit)
            out[i : i + chunk] = d[:, targets]
        return out
