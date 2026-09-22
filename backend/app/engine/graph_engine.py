import networkx as nx
from typing import Any, Dict

from app.services.data_loader import data_loader


class CourseGraphEngine:
    """Dependency graph that preserves which AND/OR branch each edge belongs to."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._curriculum_key = None
        self.build_graph()

    def _active_key(self):
        program = data_loader.get_program()
        return program["program_code"], program["curriculum_version"]

    def ensure_current(self):
        if self._curriculum_key != self._active_key():
            self.build_graph()

    def build_graph(self):
        self.graph.clear()
        for course in data_loader.get_all_courses():
            self.graph.add_node(
                course["code"],
                name=course["name"],
                credits=course.get("credits", 0.0),
                semester=course.get("suggested_semester"),
                is_compulsory=course.get("is_compulsory", False),
                category=course.get("category", ""),
            )

        for rule in data_loader.get_all_rules():
            target = rule["code"]
            branches = rule.get("condition_tree", [])
            branch_count = len(branches)
            for branch_index, branch in enumerate(branches):
                for requirement in branch:
                    source = requirement["code"]
                    if not self.graph.has_node(source):
                        source_course = data_loader.get_course(source)
                        self.graph.add_node(
                            source,
                            name=source_course["name"] if source_course else source,
                            credits=source_course.get("credits", 0.0) if source_course else 0.0,
                            semester=source_course.get("suggested_semester") if source_course else None,
                            is_compulsory=False,
                            category="Học phần điều kiện ngoài CTĐT",
                        )
                    if not self.graph.has_edge(source, target):
                        self.graph.add_edge(
                            source,
                            target,
                            types=set(),
                            branch_indexes=set(),
                            branch_count=branch_count,
                        )
                    edge = self.graph[source][target]
                    edge["types"].add(requirement.get("type", "PRIOR"))
                    edge["branch_indexes"].add(branch_index)

        for _, _, edge in self.graph.edges(data=True):
            edge["type"] = "/".join(sorted(edge.pop("types")))
            edge["branch_indexes"] = sorted(edge["branch_indexes"])
            edge["is_unavoidable"] = (
                edge["branch_count"] > 0
                and len(edge["branch_indexes"]) == edge["branch_count"]
            )

        self._curriculum_key = self._active_key()
        print(
            f"[INFO] CourseGraphEngine: {self.graph.number_of_nodes()} nút, "
            f"{self.graph.number_of_edges()} cạnh (giữ nguyên nhánh AND/OR)."
        )

    def get_impact_analysis(self, failed_course_code: str) -> Dict[str, Any]:
        """Conservative impact: only unavoidable OR dependencies are called blocked."""
        self.ensure_current()
        if not self.graph.has_node(failed_course_code):
            return {
                "failed_course_code": failed_course_code,
                "failed_course_name": failed_course_code,
                "direct_blocked_courses": [],
                "direct_at_risk_courses": [],
                "indirect_blocked_courses": [],
                "total_blocked": 0,
                "severity": "LOW",
                "analysis": f"Môn {failed_course_code} không phải là điều kiện của môn nào trong CTĐT đang chọn.",
            }

        node = self.graph.nodes[failed_course_code]
        course_name = node.get("name", failed_course_code)
        direct_blocked = []
        direct_at_risk = []
        for successor in self.graph.successors(failed_course_code):
            edge = self.graph.get_edge_data(failed_course_code, successor)
            successor_node = self.graph.nodes[successor]
            item = {
                "code": successor,
                "name": successor_node.get("name", successor),
                "credits": successor_node.get("credits", 0.0),
                "semester": successor_node.get("semester"),
                "relation": edge.get("type", "PRIOR"),
                "affected_branches": edge.get("branch_indexes", []),
                "total_branches": edge.get("branch_count", 0),
            }
            if edge.get("is_unavoidable"):
                direct_blocked.append(item)
            else:
                item["note"] = "Còn phương án điều kiện thay thế; chưa thể kết luận bị chặn."
                direct_at_risk.append(item)

        hard_graph = nx.DiGraph(
            (source, target)
            for source, target, edge in self.graph.edges(data=True)
            if edge.get("is_unavoidable")
        )
        descendants = (
            nx.descendants(hard_graph, failed_course_code)
            if hard_graph.has_node(failed_course_code)
            else set()
        )
        direct_codes = {item["code"] for item in direct_blocked}
        indirect_blocked = []
        for code in sorted(descendants - direct_codes):
            attrs = self.graph.nodes[code]
            indirect_blocked.append({
                "code": code,
                "name": attrs.get("name", code),
                "credits": attrs.get("credits", 0.0),
                "semester": attrs.get("semester"),
            })

        total_blocked = len(direct_blocked) + len(indirect_blocked)
        severity = "HIGH" if total_blocked >= 5 else ("MEDIUM" if total_blocked >= 2 else "LOW")
        analysis = (
            f"Nếu không đạt {failed_course_code} - {course_name}: chắc chắn chặn trực tiếp "
            f"{len(direct_blocked)} môn, chặn gián tiếp {len(indirect_blocked)} môn; "
            f"{len(direct_at_risk)} môn khác còn phương án điều kiện thay thế. Mức rủi ro: {severity}."
        )
        return {
            "failed_course_code": failed_course_code,
            "failed_course_name": course_name,
            "direct_blocked_courses": direct_blocked,
            "direct_at_risk_courses": direct_at_risk,
            "indirect_blocked_courses": indirect_blocked,
            "total_blocked": total_blocked,
            "severity": severity,
            "analysis": analysis,
        }

    def get_graph_visualization_data(self) -> Dict[str, Any]:
        self.ensure_current()
        profile = data_loader.get_student_profile()
        passed_codes = {course["code"] for course in profile.get("passed_courses", [])}
        failed_codes = {course["code"] for course in profile.get("failed_courses", [])}
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            status = "PASSED" if node_id in passed_codes else ("FAILED" if node_id in failed_codes else "UNLEARNED")
            nodes.append({
                "id": node_id,
                "label": f"{node_id} - {attrs.get('name', '')}",
                "name": attrs.get("name", ""),
                "credits": attrs.get("credits", 0.0),
                "semester": attrs.get("semester"),
                "is_compulsory": attrs.get("is_compulsory", False),
                "status": status,
            })
        edges = [
            {
                "source": source,
                "target": target,
                "type": edge.get("type", "PRIOR"),
                "branch_indexes": edge.get("branch_indexes", []),
                "branch_count": edge.get("branch_count", 0),
                "is_unavoidable": edge.get("is_unavoidable", False),
            }
            for source, target, edge in self.graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}


graph_engine = CourseGraphEngine()
