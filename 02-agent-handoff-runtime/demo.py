"""离线协作 Runtime 演示。"""
from runtime import Agent, Runtime, Tool, ApprovalRequired

def main():
    rt=Runtime(max_calls=3)
    rt.add_agent(Agent("planner","planner",frozenset({"add","publish"}),frozenset({"reviewer"})))
    rt.add_agent(Agent("reviewer","reviewer",frozenset({"add"})))
    rt.add_tool(Tool("add",lambda left,right:left+right))
    rt.add_tool(Tool("publish",lambda item:f"published:{item}",requires_approval=True))
    print("tool result:",rt.call_tool("planner","add",{"left":2,"right":3}))
    print("handoff:",rt.handoff("planner","reviewer","verify the sum"))
    try: rt.call_tool("planner","publish",{"item":"report"})
    except ApprovalRequired: print("publish: blocked pending approval")
    print("approved publish:",rt.call_tool("planner","publish",{"item":"report"},approved=True))
    print("audit events:",len(rt.log.entries),"last sequence:",rt.log.entries[-1]["sequence"])

if __name__=="__main__": main()
