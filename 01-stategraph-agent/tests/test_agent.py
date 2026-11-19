import unittest
from src.graph import Checkpoint, GraphError, StateGraph


class StateGraphTests(unittest.TestCase):
    def build(self):
        g=StateGraph();g.add_node('start',lambda s:{'n':s['n']+1});g.add_node('route',lambda s:s);g.add_node('a',lambda s:{**s,'branch':'a'});g.add_node('b',lambda s:{**s,'branch':'b'});g.add_edge('start','route');g.add_conditional_edges('route',lambda s:'a' if s['n']==1 else 'b',{'a':'a','b':'b'});return g
    def test_initial_status(self): self.assertEqual(self.build().invoke({'n':0}).status,'completed')
    def test_node_transforms_state(self): self.assertEqual(self.build().invoke({'n':0}).state['n'],1)
    def test_conditional_yes_route(self): self.assertEqual(self.build().invoke({'n':0}).state['branch'],'a')
    def test_conditional_other_route(self): self.assertEqual(self.build().invoke({'n':9}).state['branch'],'b')
    def test_pause_creates_checkpoint(self):
        r=self.build().invoke({'n':0},pause_after=1);self.assertEqual(r.status,'paused');self.assertIsNotNone(r.checkpoint);self.assertEqual(r.next_node,'route')
    def test_checkpoint_resumes(self):
        g=self.build();r=g.invoke({'n':0},pause_after=1);done=g.invoke(None,checkpoint=r.checkpoint);self.assertEqual(done.state['branch'],'a');self.assertEqual(done.steps,3)
    def test_checkpoint_rejects_other_graph(self):
        r=self.build().invoke({'n':0},pause_after=1);other=StateGraph();other.add_node('different',lambda s:s)
        with self.assertRaises(GraphError):other.invoke({},checkpoint=r.checkpoint)
    def test_unknown_edge_rejected(self):
        g=StateGraph();g.add_node('a',lambda s:s)
        with self.assertRaises(ValueError):g.add_edge('a','missing')
    def test_cycles_rejected(self):
        g=StateGraph();g.add_node('a',lambda s:s);g.add_node('b',lambda s:s);g.add_edge('a','b');g.add_edge('b','a')
        with self.assertRaises(GraphError):g.validate()
    def test_missing_start_rejected(self):
        g=StateGraph()
        with self.assertRaises(GraphError):g.validate()
    def test_node_retry_then_success(self):
        attempts={'n':0}
        def flaky(s):
            attempts['n']+=1
            if attempts['n']==1:raise ValueError('transient')
            return s+1
        g=StateGraph();g.add_node('flaky',flaky,retries=1);self.assertEqual(g.invoke(2).state,3);self.assertEqual(attempts['n'],2)
    def test_node_errors_propagate(self):
        g=StateGraph();g.add_node('bad',lambda s:1/0)
        with self.assertRaises(GraphError) as ctx:g.invoke(1)
        self.assertIsNotNone(ctx.exception.__cause__)
    def test_step_budget(self):
        g=StateGraph(max_steps=1);g.add_node('start',lambda s:s+1);g.add_node('end',lambda s:s+1);g.add_edge('start','end')
        with self.assertRaises(GraphError):g.invoke(0)
    def test_events_have_sequential_sequence(self):
        events=self.build().invoke({'n':0}).events;self.assertEqual([e['sequence'] for e in events],list(range(len(events))))
    def test_state_must_be_json_serializable(self):
        with self.assertRaises(GraphError):self.build().invoke(object())
    def test_validator_failure_is_explicit(self):
        g=StateGraph();g.add_node('only-positive',lambda s:s,validator=lambda s:s>0)
        with self.assertRaises(GraphError):g.invoke(-1)
    def test_custom_model_adapter_is_optional(self):
        class Model:
            def generate(self, prompt): return "custom"
        self.assertEqual(StateGraph(model=Model()).model.generate("test"),"custom")
    def test_checkpoint_round_trip_through_json(self):
        g=self.build();paused=g.invoke({'n':0},pause_after=1)
        saved=Checkpoint.from_json(paused.checkpoint.to_json())
        self.assertEqual(g.invoke(None,checkpoint=saved).state['branch'],'a')

    def test_offline_stub_is_default(self): self.assertIn("offline",StateGraph().model.generate("ignored"))
if __name__=='__main__': unittest.main()
