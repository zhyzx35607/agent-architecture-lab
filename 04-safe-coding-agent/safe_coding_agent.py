"""基于显式临时项目根的只读检索与审批补丁。永不启动子进程。"""
from __future__ import annotations
import ast
from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import tempfile

_SECRET=re.compile(r"(?i)(?:password|secret|token|api[_-]?key|access[_-]?key)\s*[:=]\s*(['\"]).+?\1")
_PRIVATE_NAMES={".env",".env.local",".env.production","id_rsa","credentials.json","secrets.json"}

from typing import Protocol

class ModelAdapter(Protocol):
    def review(self, code: str) -> str: ...

@dataclass(frozen=True)
class OfflineReviewer:
    def review(self, code: str) -> str:
        return "offline review: model calls are disabled"
class Rejected(ValueError):pass
class StalePatch(Rejected):pass

@dataclass(frozen=True)
class SearchHit:
    path:str
    line:int
@dataclass(frozen=True)
class Proposal:
    path:str
    old_text:str
    new_text:str
    base_sha:str
    patch_sha:str
@dataclass(frozen=True)
class Approval:
    patch_sha:str
    base_sha:str
    token:str

class SafeCodingAgent:
    """Inspect and stage edits within an explicitly provisioned sandbox root."""
    def __init__(self, sandbox_root: str|os.PathLike[str], *, max_file_bytes:int=1_000_000, model:ModelAdapter|None=None):
        self.root=Path(sandbox_root).resolve(strict=True)
        if not self.root.is_dir():raise Rejected("sandbox root must be a directory")
        if max_file_bytes<1:raise ValueError("max_file_bytes must be positive")
        self.max_file_bytes=max_file_bytes
        self.model=model or OfflineReviewer()
        self._approvals={}
        self._consumed=set()
    def review_source(self, relative: str) -> str:
        """只把通过安全读取检查的源码交给显式注入的审查模型。"""
        source=self._read_bytes(relative).decode("utf-8")
        return self.model.review(source)
    def _path(self,relative:str)->Path:
        rel=Path(relative)
        if rel.is_absolute() or not relative or ".." in rel.parts:raise Rejected("unsafe relative path")
        if any(part.startswith(".") or part.lower() in _PRIVATE_NAMES or ".git" in part.lower() for part in rel.parts):raise Rejected("hidden or sensitive path blocked")
        if rel.suffix.lower() not in {".py",".md",".txt"}:raise Rejected("file type not allowed")
        p=(self.root/rel).resolve(strict=False)
        try:p.relative_to(self.root)
        except ValueError as exc:raise Rejected("path escapes sandbox") from exc
        return p
    def _read_bytes(self,relative:str)->bytes:
        p=self._path(relative)
        try:
            size=p.stat().st_size
            if size>self.max_file_bytes:raise Rejected("file exceeds size limit")
            data=p.read_bytes()
        except FileNotFoundError:raise Rejected("file not found")
        if len(data)>self.max_file_bytes:raise Rejected("file exceeds size limit")
        if b"\x00" in data:raise Rejected("binary file blocked")
        if _SECRET.search(data.decode("utf-8",errors="strict")):raise Rejected("sensitive content blocked")
        return data
    def search(self,query:str)->list[SearchHit]:
        q=query.casefold();hits=[]
        if not q:return hits
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():continue
            rel=p.relative_to(self.root).as_posix()
            try:data=self._read_bytes(rel).decode("utf-8")
            except (Rejected,UnicodeDecodeError):continue
            hits.extend(SearchHit(rel,n) for n,line in enumerate(data.splitlines(),1) if q in line.casefold())
        return hits
    def propose_patch(self,relative:str,old_text:str,new_text:str)->Proposal:
        original=self._read_bytes(relative).decode("utf-8")
        if not old_text or original.count(old_text)!=1:raise Rejected("patch anchor must match exactly once")
        candidate=original.replace(old_text,new_text,1)
        if _SECRET.search(candidate):raise Rejected("patch would introduce sensitive content")
        base=hashlib.sha256(original.encode()).hexdigest()
        material="\0".join((relative,base,old_text,new_text)).encode()
        digest=hashlib.sha256(material).hexdigest()
        return Proposal(relative,old_text,new_text,base,digest)
    def approve(self,proposal:Proposal,displayed_digest:str)->Approval:
        if not hmac.compare_digest(proposal.patch_sha,displayed_digest):raise Rejected("patch digest mismatch")
        current=self._read_bytes(proposal.path).decode("utf-8")
        if hashlib.sha256(current.encode()).hexdigest()!=proposal.base_sha:raise StalePatch("base changed since review")
        token=secrets.token_urlsafe(24)
        receipt=Approval(proposal.patch_sha,proposal.base_sha,token)
        self._approvals[token]=receipt
        return receipt
    def apply(self,proposal:Proposal,approval:Approval)->Path:
        registered=self._approvals.get(approval.token)
        if registered!=approval or approval.patch_sha!=proposal.patch_sha or approval.base_sha!=proposal.base_sha:raise Rejected("approval is invalid or altered")
        if approval.token in self._consumed:raise Rejected("approval was already consumed")
        original=self._read_bytes(proposal.path).decode("utf-8")
        if hashlib.sha256(original.encode()).hexdigest()!=proposal.base_sha:raise StalePatch("file changed after approval")
        if original.count(proposal.old_text)!=1:raise StalePatch("patch anchor changed")
        candidate=original.replace(proposal.old_text,proposal.new_text,1)
        if _SECRET.search(candidate):raise Rejected("patch contains sensitive material")
        if proposal.path.lower().endswith(".py"):
            try:ast.parse(candidate,filename=proposal.path)
            except SyntaxError as exc:raise Rejected("patch has invalid Python syntax") from exc
        target=self._path(proposal.path);target.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".agent-patch-",suffix=".tmp",dir=target.parent)
        try:
            with os.fdopen(fd,"w",encoding="utf-8",newline="") as stream:stream.write(candidate)
            current=self._read_bytes(proposal.path).decode("utf-8")
            if hashlib.sha256(current.encode()).hexdigest()!=proposal.base_sha:raise StalePatch("file changed before commit")
            os.replace(tmp,target);self._consumed.add(approval.token);return target
        finally:
            try:os.unlink(tmp)
            except FileNotFoundError:pass
    @staticmethod
    def verify_python(code:str)->bool:
        try:ast.parse(code);return True
        except SyntaxError:return False
