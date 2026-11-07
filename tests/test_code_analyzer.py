import os
import tempfile
import pytest
from app.core.code_analyzer import CodeAnalyzer


def test_code_analyzer_ast_and_summary():
    analyzer = CodeAnalyzer()

    # Create temporary mini-repo
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a sample python file with class, function, and import
        core_dir = os.path.join(tmp_dir, "core")
        os.makedirs(core_dir)

        sample_file = os.path.join(core_dir, "user_service.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "import os\n"
                "from typing import Optional\n\n"
                "class UserModel:\n"
                "    pass\n\n"
                "def get_user_by_id(user_id: int) -> Optional[UserModel]:\n"
                "    return None\n"
            )

        analysis = analyzer.analyze_repository(tmp_dir, "test_repo")

        assert analysis["repo_name"] == "test_repo"
        assert analysis["total_files"] == 1
        assert "Python" in analysis["languages"]
        assert "core" in analysis["components"]
        assert len(analysis["files"]) == 1

        file_info = analysis["files"][0]
        assert "UserModel" in file_info["classes"]
        assert "get_user_by_id" in file_info["functions"]

        # Verify 3-sentence summary format
        summary = analysis["summary"]
        assert isinstance(summary, str)
        # Check that it contains 3 distinct sentences
        sentences = [s.strip() for s in summary.split(".") if s.strip()]
        assert len(sentences) >= 3

        # Verify Cypher query generation
        cyphers = analyzer.generate_initial_cypher(analysis)
        assert len(cyphers) > 0
        assert any("MERGE (r:Repository" in q for q in cyphers)
        assert any("MERGE (c:Component" in q for q in cyphers)
        assert any("MERGE (f:File" in q for q in cyphers)
