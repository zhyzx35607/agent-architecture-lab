import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from safe_coding_agent import Approval, OfflineReviewer, Rejected, SafeCodingAgent, StalePatch

class CodingAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'app.py').write_text('def total(items):\n    return sum(items)\n',encoding='utf-8');self.agent=SafeCodingAgent(self.root)
    def proposal(self):return self.agent.propose_patch('app.py','return sum(items)','return sum(items, 0)')
    def test_search_returns_only_safe_source_locations(self):self.assertEqual(self.agent.search('sum')[0].path,'app.py')
    def test_python_ast_valid_and_invalid(self):self.assertTrue(self.agent.verify_python('x = 1'));self.assertFalse(self.agent.verify_python('if:'))
    def test_proposal_is_reviewable_and_hash_stable(self):self.assertEqual(self.proposal().patch_sha,self.proposal().patch_sha)
    def test_patch_requires_exact_digest_approval(self):
        with self.assertRaises(Rejected):self.agent.approve(self.proposal(),'0'*64)
    def test_approved_patch_changes_only_sandbox_file(self):
        p=self.proposal();a=self.agent.approve(p,p.patch_sha);path=self.agent.apply(p,a);self.assertEqual(path.read_text(),'def total(items):\n    return sum(items, 0)\n')
    def test_approval_is_one_use(self):
        p=self.proposal();a=self.agent.approve(p,p.patch_sha);self.agent.apply(p,a)
        with self.assertRaises(Rejected):self.agent.apply(p,a)
    def test_changed_base_rejected_at_approval(self):
        p=self.proposal();(self.root/'app.py').write_text('changed',encoding='utf-8')
        with self.assertRaises(StalePatch):self.agent.approve(p,p.patch_sha)
    def test_change_after_approval_rejected_at_commit(self):
        p=self.proposal();a=self.agent.approve(p,p.patch_sha);(self.root/'app.py').write_text('changed',encoding='utf-8')
        with self.assertRaises(StalePatch):self.agent.apply(p,a)
    def test_forged_receipt_rejected(self):
        p=self.proposal();a=self.agent.approve(p,p.patch_sha);forged=Approval(a.patch_sha,a.base_sha,'not-the-token')
        with self.assertRaises(Rejected):self.agent.apply(p,forged)
    def test_path_traversal_rejected(self):
        with self.assertRaises(Rejected):self.agent.propose_patch('../outside.py','x','y')
    def test_absolute_outside_path_rejected(self):
        with self.assertRaises(Rejected):self.agent.propose_patch(str(self.root.parent),'x','y')
    def test_binary_blocked(self):
        (self.root/'binary.py').write_bytes(b'\x00\x01')
        with self.assertRaises(Rejected):self.agent.propose_patch('binary.py','x','y')
    def test_large_file_blocked(self):
        (self.root/'huge.txt').write_text('x'*128,encoding='utf-8');small=SafeCodingAgent(self.root,max_file_bytes=16)
        with self.assertRaises(Rejected):small.propose_patch('huge.txt','x','y')
    def test_secret_file_never_returned(self):
        (self.root/'credentials.py').write_text("password = 'dummy-secret'\n",encoding='utf-8')
        with self.assertRaises(Rejected):self.agent.propose_patch('credentials.py','dummy-secret','redacted')
    def test_hidden_and_env_paths_rejected(self):
        (self.root/'.env').write_text('TOKEN=placeholder',encoding='utf-8')
        with self.assertRaises(Rejected):self.agent.propose_patch('.env','TOKEN','SAFE')
    def test_symlink_escape_rejected(self):
        outside=self.root.parent/'outside-target.py'
        try:(self.root/'link.py').symlink_to(outside)
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable on this host')
        with self.assertRaises(Rejected):self.agent.propose_patch('link.py','x','y')
    def test_python_syntax_checked_before_apply(self):
        proposal=self.agent.propose_patch('app.py','return sum(items)','if:')
        receipt=self.agent.approve(proposal,proposal.patch_sha)
        with self.assertRaises(Rejected):self.agent.apply(proposal,receipt)

    def test_offline_reviewer_is_local(self): self.assertIn("offline",OfflineReviewer().review("x = 1"))
    def test_custom_review_adapter_is_optional(self):
        model=type("LocalReview",(),{"review":lambda self,code:"custom review"})()
        self.assertEqual(SafeCodingAgent(self.root,model=model).model.review("x"),"custom review")
    def test_default_reviewer_receives_valid_sandbox_source(self):
        self.assertIn("offline",self.agent.review_source('app.py'))
