"""Enriquecimento por grafo temporal, sem transformar associação em culpa."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .models import Finding, RelationshipEdge


class TemporalGraphEnricher:
    def __init__(self, edges: tuple[RelationshipEdge, ...], as_of: datetime) -> None:
        self.edges = tuple(
            edge
            for edge in edges
            if edge.valid_from <= as_of and (edge.valid_to is None or edge.valid_to >= as_of)
        )
        self.neighbors: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            self.neighbors[edge.from_id].add(edge.to_id)
            self.neighbors[edge.to_id].add(edge.from_id)

    def enrich(self, finding: Finding) -> Finding:
        direct = self.neighbors.get(finding.subject_id, set())
        peers: set[str] = set()
        shared_neighbor_count = 0
        for neighbor in direct:
            neighbor_peers = self.neighbors.get(neighbor, set()) - {finding.subject_id}
            peers.update(neighbor_peers)
            shared_neighbor_count += len(neighbor_peers)
        connectivity = min(1.0, (len(direct) + shared_neighbor_count * 0.5) / 5)
        features = dict(finding.feature_values)
        features.update(
            {
                "graph_degree": len(direct),
                "graph_shared_neighbor_peers": len(peers),
                "graph_connectivity": round(connectivity, 6),
            }
        )
        reasons = list(finding.reason_codes)
        if shared_neighbor_count > 0:
            reasons.append("TEMPORAL_GRAPH_RELATION_RELEVANT")
        return finding.model_copy(update={"feature_values": features, "reason_codes": tuple(reasons)})

