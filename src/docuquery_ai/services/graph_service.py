import networkx as nx
from typing import Any, Dict, List, Optional

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None):
        if not self.graph.has_node(node_id):
            self.graph.add_node(node_id, type=node_type, **(properties or {}))
            #print(f"Added node: {node_id} ({node_type})")

    def add_edge(self, u_node_id: str, v_node_id: str, edge_type: str, properties: Optional[Dict[str, Any]] = None):
        if self.graph.has_node(u_node_id) and self.graph.has_node(v_node_id):
            self.graph.add_edge(u_node_id, v_node_id, type=edge_type, **(properties or {}))
            #print(f"Added edge: {u_node_id} -[{edge_type}]-> {v_node_id}")
        else:
            #print(f"Warning: Could not add edge. One or both nodes not found: {u_node_id}, {v_node_id}")
            pass

    def get_node(self, node_id: str):
        return self.graph.nodes.get(node_id)

    def get_edges(self, u_node_id: str):
        return list(self.graph.edges(u_node_id, data=True))

    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for node_id, data in self.graph.nodes(data=True):
            match = False
            if node_type and data.get("type") != node_type:
                continue
            
            # Simple keyword search for demonstration
            if query.lower() in node_id.lower():
                match = True
            else:
                for prop_key, prop_value in data.items():
                    if isinstance(prop_value, str) and query.lower() in prop_value.lower():
                        match = True
                        break
            if match:
                results.append({"id": node_id, "properties": data})
        return results

    def to_json(self):
        from networkx.readwrite import json_graph
        return json_graph.node_link_data(self.graph)

    def from_json(self, json_data):
        from networkx.readwrite import json_graph
        self.graph = json_graph.node_link_graph(json_data)

    def save_graph(self, path: str):
        import pickle
        with open(path, "wb") as f:
            pickle.dump(self.graph, f)
        print(f"Knowledge graph saved to {path}")

    def load_graph(self, path: str):
        import pickle
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.graph = pickle.load(f)
            print(f"Knowledge graph loaded from {path}")
            return True
        return False

# Global instance for simplicity, can be managed by a client class
knowledge_graph = KnowledgeGraph()
GRAPH_DB_PATH = os.path.join(settings.VECTOR_STORE_PATH, "knowledge_graph.pkl")

def initialize_knowledge_graph():
    global knowledge_graph
    if not knowledge_graph.load_graph(GRAPH_DB_PATH):
        print("No existing knowledge graph found, initializing new one.")
        knowledge_graph = KnowledgeGraph()
    return knowledge_graph

def get_knowledge_graph():
    global knowledge_graph
    return knowledge_graph

def save_knowledge_graph():
    global knowledge_graph
    knowledge_graph.save_graph(GRAPH_DB_PATH)
