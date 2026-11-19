from src.graph import GraphError, StateGraph


def increment(state):
    return {**state, "value": state["value"] + 1}


def main():
    graph = StateGraph()
    graph.add_node("collect", increment)
    graph.add_node("route", lambda s: s)
    graph.add_node("approved", lambda s: {**s, "result": "approved"})
    graph.add_node("review", lambda s: {**s, "result": "review"})
    graph.add_edge("collect", "route")
    graph.add_conditional_edges("route", lambda s: "ok" if s["value"] > 0 else "review",
                                {"ok": "approved", "review": "review"})
    first = graph.invoke({"value": 0}, pause_after=2)
    print(f"First pass: {first.status}; value={first.state['value']}; resume-at={first.next_node}")
    final = graph.invoke({}, checkpoint=first.checkpoint)
    print(f"Resume: {final.status}; result={final.state['result']}; steps={final.steps}")
    print("Audited events:", len(final.events))


if __name__ == "__main__":
    main()
