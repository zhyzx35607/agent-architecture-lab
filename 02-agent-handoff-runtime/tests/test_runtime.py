import unittest
from runtime import Agent, ApprovalRequired, BudgetExceeded, PermissionDenied, Runtime, Tool

class RuntimeTests(unittest.TestCase):
    def make(self, budget=5):
        r=Runtime(max_calls=budget);r.add_agent(Agent('a','planner',frozenset({'sum'}),frozenset({'b'})));r.add_agent(Agent('b','reviewer',frozenset({'sum'})));r.add_tool(Tool('sum',lambda left,right:left+right));return r
    def test_tool_success(self): self.assertEqual(self.make().call_tool('a','sum',{'left':1,'right':2}),3)
    def test_tool_permission(self):
        with self.assertRaises(PermissionDenied):self.make().call_tool('b','missing',{})
    def test_unknown_actor(self):
        with self.assertRaises(PermissionDenied):self.make().call_tool('missing','sum',{})
    def test_approval_blocks(self):
        r=self.make();r.add_tool(Tool('publish',lambda item:item,requires_approval=True))
        r.agents['a']=Agent('a','planner',frozenset({'sum','publish'}),frozenset({'b'}))
        with self.assertRaises(ApprovalRequired):r.call_tool('a','publish',{'item':'x'})
    def test_approval_allows(self):
        r=self.make();r.add_tool(Tool('publish',lambda item:item,requires_approval=True));r.agents['a']=Agent('a','planner',frozenset({'sum','publish'}),frozenset({'b'}));self.assertEqual(r.call_tool('a','publish',{'item':'x'},approved=True),'x')
    def test_handoff_success(self): self.assertIn('b accepted',self.make().handoff('a','b','review'))
    def test_handoff_denied(self):
        r=self.make()
        with self.assertRaises(PermissionDenied):r.handoff('b','a','review')
    def test_handoff_unknown(self):
        with self.assertRaises(PermissionDenied):self.make().handoff('a','z','review')
    def test_audit_sequence(self):
        r=self.make();r.call_tool('a','sum',{'left':1,'right':1});self.assertEqual([e['sequence'] for e in r.log.entries],list(range(len(r.log.entries))))
    def test_budget(self):
        r=self.make(1);r.call_tool('a','sum',{'left':1,'right':1})
        with self.assertRaises(BudgetExceeded):r.call_tool('a','sum',{'left':1,'right':1})
    def test_plan(self): self.assertEqual(self.make().run_plan('a',[{'kind':'tool','name':'sum','args':{'left':4,'right':5}}]),[9])
    def test_tool_errors_are_logged(self):
        r=self.make();r.add_tool(Tool('bad',lambda:1/0));r.agents['a']=Agent('a','planner',frozenset({'sum','bad'}),frozenset({'b'}))
        with self.assertRaises(ZeroDivisionError):r.call_tool('a','bad',{})
        self.assertEqual(r.log.entries[-1]['outcome'],'error')
    def test_model_stub_is_offline(self): self.assertTrue(self.make().model.respond('x').startswith('offline'))
    def test_duplicate_registration(self):
        r=self.make()
        with self.assertRaises(ValueError):r.add_agent(Agent('a','duplicate'))
    def test_custom_model_adapter_is_optional(self):
        custom=type("CustomModel",(),{"respond":lambda self,prompt:"custom"})()
        self.assertEqual(Runtime(model=custom).model.respond("test"),"custom")
    def test_duplicate_agent_registration_is_rejected(self):
        r=self.make()
        with self.assertRaises(ValueError):r.add_agent(Agent('a','duplicate'))

if __name__=='__main__':unittest.main()
