"""
Integration tests for ActivateSkillTool and ArxivSearchTool.

Tests verify:
1. Both tools import successfully
2. Both tools instantiate without errors
3. ArxivSearchTool can query arXiv API
4. ActivateSkillTool works with a mock registry
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add workspace to path
sys.path.insert(0, '/Users/zc/PycharmProjects/nano_agent_team_selfevolve/evolution_sessions/nano_agent_evo_20260308_000429/.blackboard/resources/workspace')


class TestActivateSkillTool:
    """Test cases for ActivateSkillTool"""

    def test_import_activate_skill_tool(self):
        """Test 1: Verify ActivateSkillTool imports successfully"""
        from backend.tools.activate_skill import ActivateSkillTool
        assert ActivateSkillTool is not None
        assert hasattr(ActivateSkillTool, 'execute')
        assert hasattr(ActivateSkillTool, 'name')
        assert hasattr(ActivateSkillTool, 'description')
        assert hasattr(ActivateSkillTool, 'parameters_schema')

    def test_instantiate_activate_skill_tool(self):
        """Test 2: Verify ActivateSkillTool instantiates without errors"""
        from backend.tools.activate_skill import ActivateSkillTool
        
        # Test with no registry
        tool = ActivateSkillTool()
        assert tool is not None
        assert tool.name == "activate_skill"
        assert tool.skill_registry is None
        
        # Test with mock registry
        mock_registry = Mock()
        tool_with_registry = ActivateSkillTool(skill_registry=mock_registry)
        assert tool_with_registry.skill_registry is mock_registry

    def test_parameters_schema(self):
        """Test 3: Verify parameters_schema is correct"""
        from backend.tools.activate_skill import ActivateSkillTool
        
        tool = ActivateSkillTool()
        schema = tool.parameters_schema
        
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'skill_name' in schema['properties']
        assert schema['properties']['skill_name']['type'] == 'string'
        assert 'skill_name' in schema['required']

    def test_execute_without_registry(self):
        """Test 4: Verify execute returns error when no registry"""
        from backend.tools.activate_skill import ActivateSkillTool
        
        tool = ActivateSkillTool()
        result = tool.execute(skill_name="test_skill")
        
        assert "Error: Skill registry not initialized" in result

    def test_execute_with_mock_registry(self):
        """Test 5: Verify ActivateSkillTool works with mock registry"""
        from backend.tools.activate_skill import ActivateSkillTool
        
        # Create mock skill object
        mock_skill = Mock()
        mock_skill.name = "test-driven-development"
        mock_skill.path = "/Users/zc/PycharmProjects/nano_agent_team_selfevolve/evolution_sessions/nano_agent_evo_20260308_000429/.blackboard/resources/workspace/.skills/test-driven-development"
        mock_skill.instructions = "This is a test skill instruction.\nFollow these steps:\n1. Step one\n2. Step two"
        
        # Create mock registry
        mock_registry = Mock()
        mock_registry.get_skill.return_value = mock_skill
        
        tool = ActivateSkillTool(skill_registry=mock_registry)
        result = tool.execute(skill_name="test-driven-development")
        
        # Verify registry was called
        mock_registry.get_skill.assert_called_once_with("test-driven-development")
        
        # Verify result contains expected content
        assert "SKILL ACTIVATED: test-driven-development" in result
        assert "Skill Base Path:" in result
        assert "Instructions:" in result
        assert "This is a test skill instruction." in result
        assert "END SKILL" in result

    def test_execute_skill_not_found(self):
        """Test 6: Verify execute handles skill not found"""
        from backend.tools.activate_skill import ActivateSkillTool
        
        mock_registry = Mock()
        mock_registry.get_skill.return_value = None
        
        tool = ActivateSkillTool(skill_registry=mock_registry)
        result = tool.execute(skill_name="nonexistent_skill")
        
        assert "Error: Skill 'nonexistent_skill' not found" in result


class TestArxivSearchTool:
    """Test cases for ArxivSearchTool"""

    def test_import_arxiv_search_tool(self):
        """Test 1: Verify ArxivSearchTool imports successfully"""
        from backend.tools.arxiv_search import ArxivSearchTool
        assert ArxivSearchTool is not None
        assert hasattr(ArxivSearchTool, 'execute')
        assert hasattr(ArxivSearchTool, 'name')
        assert hasattr(ArxivSearchTool, 'description')
        assert hasattr(ArxivSearchTool, 'parameters_schema')

    def test_instantiate_arxiv_search_tool(self):
        """Test 2: Verify ArxivSearchTool instantiates without errors"""
        from backend.tools.arxiv_search import ArxivSearchTool
        
        tool = ArxivSearchTool()
        assert tool is not None
        assert tool.name == "arxiv_search"

    def test_parameters_schema(self):
        """Test 3: Verify parameters_schema is correct"""
        from backend.tools.arxiv_search import ArxivSearchTool
        
        tool = ArxivSearchTool()
        schema = tool.parameters_schema
        
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'query' in schema['properties']
        assert schema['properties']['query']['type'] == 'string'
        assert 'max_results' in schema['properties']
        assert schema['properties']['max_results']['type'] == 'integer'
        assert 'query' in schema['required']

    def test_to_openai_schema(self):
        """Test 4: Verify to_openai_schema returns correct format"""
        from backend.tools.arxiv_search import ArxivSearchTool
        
        tool = ArxivSearchTool()
        schema = tool.to_openai_schema()
        
        assert schema['type'] == 'function'
        assert 'function' in schema
        assert schema['function']['name'] == 'arxiv_search'
        assert 'description' in schema['function']
        assert 'parameters' in schema['function']

    def test_arxiv_api_query(self):
        """Test 5: Verify ArxivSearchTool can query arXiv API"""
        from backend.tools.arxiv_search import ArxivSearchTool
        
        tool = ArxivSearchTool()
        
        # Query for a well-known paper topic
        result = tool.execute(query="all:attention is all you need", max_results=2)
        
        # Should not return an error
        assert not result.startswith("Error")
        
        # Should return some results (at least one paper)
        assert len(result) > 0
        assert "[1]" in result or "No results found" in result
        
        # If results found, verify structure
        if "No results found" not in result:
            assert "Authors:" in result
            assert "Link:" in result
            assert "Summary:" in result

    def test_arxiv_api_empty_results(self):
        """Test 6: Verify handling of empty results"""
        from backend.tools.arxiv_search import ArxivSearchTool
        
        tool = ArxivSearchTool()
        
        # Query for something that likely doesn't exist
        result = tool.execute(query="all:xyznonexistent123456", max_results=5)
        
        # Should either return "No results found" or some results
        # (arXiv might have fuzzy matching)
        assert isinstance(result, str)
        assert not result.startswith("Error: arXiv API returned status code")


class TestToolIntegration:
    """Integration tests for both tools together"""

    def test_both_tools_import(self):
        """Test 1: Verify both tools can be imported together"""
        from backend.tools.activate_skill import ActivateSkillTool
        from backend.tools.arxiv_search import ArxivSearchTool
        
        assert ActivateSkillTool is not None
        assert ArxivSearchTool is not None

    def test_both_tools_instantiate(self):
        """Test 2: Verify both tools can be instantiated together"""
        from backend.tools.activate_skill import ActivateSkillTool
        from backend.tools.arxiv_search import ArxivSearchTool
        
        skill_tool = ActivateSkillTool()
        arxiv_tool = ArxivSearchTool()
        
        assert skill_tool is not None
        assert arxiv_tool is not None
        assert skill_tool.name == "activate_skill"
        assert arxiv_tool.name == "arxiv_search"

    def test_tools_registered_in_tool_registry(self):
        """Test 3: Verify both tools are registered in tool_registry.py"""
        from backend.llm.tool_registry import ToolRegistry, ActivateSkillTool, ArxivSearchTool
        
        registry = ToolRegistry()
        
        # Register both tools as done in bootstrap_llm
        registry.register_tool_class("activate_skill", ActivateSkillTool)
        registry.register_tool_class("arxiv_search", ArxivSearchTool)
        
        # Verify they can be created
        skill_tool = registry.create_tool("activate_skill")
        arxiv_tool = registry.create_tool("arxiv_search")
        
        assert skill_tool is not None
        assert arxiv_tool is not None
        assert isinstance(skill_tool, ActivateSkillTool)
        assert isinstance(arxiv_tool, ArxivSearchTool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
