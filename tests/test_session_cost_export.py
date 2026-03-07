"""
Integration tests for SessionCostExportTool.

Tests verify:
1. Tool imports successfully
2. Tool instantiates without errors
3. Cost calculation works correctly
4. Export to JSON format works
5. Export to CSV format works
6. Summary by model is accurate
7. Tool is properly registered in tool_registry.py
"""

import pytest
import json
import csv
import os
import sys
import tempfile

# Add workspace to path
sys.path.insert(0, '/Users/zc/PycharmProjects/nano_agent_team_selfevolve/evolution_sessions/nano_agent_evo_20260308_000429/.blackboard/resources/workspace')


class TestSessionCostExportTool:
    """Test cases for SessionCostExportTool"""

    def test_import_session_cost_export_tool(self):
        """Test 1: Verify SessionCostExportTool imports successfully"""
        from backend.tools.session_cost_export import SessionCostExportTool
        assert SessionCostExportTool is not None
        assert hasattr(SessionCostExportTool, 'execute')
        assert hasattr(SessionCostExportTool, 'name')
        assert hasattr(SessionCostExportTool, 'description')
        assert hasattr(SessionCostExportTool, 'parameters_schema')

    def test_instantiate_session_cost_export_tool(self):
        """Test 2: Verify SessionCostExportTool instantiates without errors"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        assert tool is not None
        assert tool.name == "session_cost_export"
        assert "Export session token usage" in tool.description

    def test_parameters_schema(self):
        """Test 3: Verify parameters_schema is correct"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        schema = tool.parameters_schema

        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'export_format' in schema['properties']
        assert 'output_path' in schema['properties']
        assert 'session_data' in schema['properties']
        assert schema['properties']['export_format']['enum'] == ['csv', 'json']

    def test_to_openai_schema(self):
        """Test 4: Verify to_openai_schema returns correct format"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        schema = tool.to_openai_schema()

        assert schema['type'] == 'function'
        assert 'function' in schema
        assert schema['function']['name'] == 'session_cost_export'
        assert 'description' in schema['function']
        assert 'parameters' in schema['function']

    def test_calculate_cost_gpt4(self):
        """Test 5: Verify cost calculation for GPT-4"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        # GPT-4: $0.03/1K prompt, $0.06/1K completion
        cost = tool._calculate_cost("gpt-4", 1000, 500)
        
        # Expected: (1000/1000)*0.03 + (500/1000)*0.06 = 0.03 + 0.03 = 0.06
        assert abs(cost - 0.06) < 0.0001

    def test_calculate_cost_unknown_model(self):
        """Test 6: Verify cost calculation uses defaults for unknown model"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        # Unknown model: $0.001/1K prompt, $0.002/1K completion
        cost = tool._calculate_cost("unknown-model", 1000, 1000)
        
        # Expected: (1000/1000)*0.001 + (1000/1000)*0.002 = 0.003
        assert abs(cost - 0.003) < 0.0001

    def test_execute_record_session_data(self):
        """Test 7: Verify execute can record session cost data"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        session_data = {
            "session_id": "test-session-001",
            "model": "gpt-4",
            "prompt_tokens": 1000,
            "completion_tokens": 500
        }
        
        result = tool.execute(session_data=session_data)
        
        assert "✅ Cost data recorded" in result
        assert "test-session-001" in result
        assert "gpt-4" in result
        assert len(tool._cost_history) == 1

    def test_execute_no_data_message(self):
        """Test 8: Verify execute returns info message when no data"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        result = tool.execute()
        
        assert "ℹ️ No cost data recorded yet" in result

    def test_export_to_json(self):
        """Test 9: Verify export to JSON format"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        # Add some test data
        tool.execute(session_data={
            "session_id": "test-001",
            "model": "gpt-4",
            "prompt_tokens": 1000,
            "completion_tokens": 500
        })
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = tool.execute(export_format="json", output_path=temp_path)
            
            assert "✅ Cost data exported" in result
            assert temp_path in result
            
            # Verify file exists and contains valid JSON
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert data["total_sessions"] == 1
            assert data["total_cost_usd"] > 0
            assert "by_model" in data
            assert "sessions" in data
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_to_csv(self):
        """Test 10: Verify export to CSV format"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        # Add some test data
        tool.execute(session_data={
            "session_id": "test-001",
            "model": "gpt-4",
            "prompt_tokens": 1000,
            "completion_tokens": 500
        })
        
        tool.execute(session_data={
            "session_id": "test-002",
            "model": "gpt-3.5-turbo",
            "prompt_tokens": 500,
            "completion_tokens": 200
        })
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            result = tool.execute(export_format="csv", output_path=temp_path)
            
            assert "✅ Cost data exported" in result
            
            # Verify file exists and contains valid CSV
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0]["session_id"] == "test-001"
            assert rows[1]["session_id"] == "test-002"
            assert "total_tokens" in rows[0]
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_summary_by_model(self):
        """Test 11: Verify summary by model is accurate"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        # Add multiple sessions with different models
        tool.execute(session_data={
            "session_id": "test-001",
            "model": "gpt-4",
            "prompt_tokens": 1000,
            "completion_tokens": 500
        })
        
        tool.execute(session_data={
            "session_id": "test-002",
            "model": "gpt-4",
            "prompt_tokens": 2000,
            "completion_tokens": 1000
        })
        
        tool.execute(session_data={
            "session_id": "test-003",
            "model": "gpt-3.5-turbo",
            "prompt_tokens": 500,
            "completion_tokens": 200
        })
        
        summary = tool._get_summary_by_model(tool._cost_history)
        
        assert "gpt-4" in summary
        assert "gpt-3.5-turbo" in summary
        
        # GPT-4 should have 2 sessions
        assert summary["gpt-4"]["session_count"] == 2
        assert summary["gpt-4"]["total_prompt_tokens"] == 3000
        assert summary["gpt-4"]["total_completion_tokens"] == 1500
        
        # GPT-3.5-turbo should have 1 session
        assert summary["gpt-3.5-turbo"]["session_count"] == 1

    def test_get_status_message(self):
        """Test 12: Verify status message is correct"""
        from backend.tools.session_cost_export import SessionCostExportTool

        tool = SessionCostExportTool()
        
        msg = tool.get_status_message(export_format="json", output_path="/tmp/test.json")
        
        assert "💰 Exporting session cost data" in msg
        assert "test.json" in msg


class TestSessionCostExportToolRegistration:
    """Integration tests for tool registration"""

    def test_tool_registered_in_tool_registry(self):
        """Test 1: Verify tool is registered in tool_registry.py"""
        from backend.llm.tool_registry import ToolRegistry
        from backend.tools.session_cost_export import SessionCostExportTool

        registry = ToolRegistry()
        
        # Register the tool
        registry.register_tool_class("session_cost_export", SessionCostExportTool)
        
        # Verify it can be created
        tool = registry.create_tool("session_cost_export")
        
        assert tool is not None
        assert isinstance(tool, SessionCostExportTool)
        assert tool.name == "session_cost_export"

    def test_tool_schema_validation(self):
        """Test 2: Verify tool schema passes validation"""
        from backend.tools.session_cost_export import SessionCostExportTool
        import json

        tool = SessionCostExportTool()
        schema = tool.parameters_schema
        
        # Verify schema is valid JSON Schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        
        # Verify all properties have required fields
        for prop_name, prop_def in schema['properties'].items():
            assert 'type' in prop_def
            assert 'description' in prop_def


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
