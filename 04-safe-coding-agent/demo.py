"""Safe patch demo. Everything is confined to a temporary subdirectory under this project."""
from pathlib import Path
import tempfile
from safe_coding_agent import SafeCodingAgent

def main():
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="safe-coding-demo-",dir=root) as directory:
        file=Path(directory)/"sample.py";file.write_text("def total(items):\n    return sum(items)\n",encoding="utf-8")
        agent=SafeCodingAgent(directory);print("Indexed:",agent.search("sum"))
        proposal=agent.propose_patch("sample.py","return sum(items)","return sum(items, 0)")
        print("Reviewed patch SHA-256:",proposal.patch_sha)
        receipt=agent.approve(proposal,proposal.patch_sha)
        changed=agent.apply(proposal,receipt)
        print("Approved patch applied within owned temporary sandbox:",changed.parent==Path(directory).resolve())
        print("AST validation:",agent.verify_python(file.read_text(encoding="utf-8")))
    print("Temporary sandbox removed.")

if __name__=="__main__":main()
