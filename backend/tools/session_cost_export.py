"""
Session Cost Export Tool Module

Provides functionality to track, summarize, and export per-session token usage and cost data.

Features:
    - Track token usage per session via session metadata
    - Export cost data to CSV or JSON format
    - Provide cost summaries by model
    - Enable model comparison and ROI analysis

Usage:
    The tool reads cost data from session.metadata which is populated by middleware
    or LLM provider responses. It can export this data to files for analysis.
"""

import json
import csv
import os
from typing import Dict, Any, List, Optional
from backend.tools.base import BaseTool
from backend.llm.decorators import schema_strict_validator


class SessionCostExportTool(BaseTool):
    """
    Tool for exporting session cost and token usage data.
    
    This tool allows agents and users to:
    1. Track token usage per session
    2. Export cost data to CSV or JSON files
    3. Get cost summaries grouped by model
    4. Analyze spending patterns for optimization
    """

    @property
    def name(self) -> str:
        return "session_cost_export"

    @property
    def description(self) -> str:
        return "Export session token usage and cost data to CSV or JSON format. Tracks costs per model, provides summaries for ROI analysis and spending optimization. Use this after sessions to analyze expenses or compare model costs."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "export_format": {
                    "type": "string",
                    "description": "Output format: 'csv' or 'json' (default: 'json')",
                    "enum": ["csv", "json"],
                    "default": "json"
                },
                "output_path": {
                    "type": "string",
                    "description": "File path to export cost data (default: 'session_costs.json' or 'session_costs.csv')"
                },
                "session_data": {
                    "type": "object",
                    "description": "Session cost data to export (optional - if not provided, returns summary of current session)",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique session identifier"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model name used"
                        },
                        "prompt_tokens": {
                            "type": "integer",
                            "description": "Number of tokens in prompt"
                        },
                        "completion_tokens": {
                            "type": "integer",
                            "description": "Number of tokens in completion"
                        },
                        "cost_usd": {
                            "type": "number",
                            "description": "Cost in USD"
                        }
                    }
                }
            },
            "required": []
        }

    def __init__(self):
        super().__init__()
        # Cost tracking storage (in-memory for now, can be extended to persistent storage)
        self._cost_history: List[Dict[str, Any]] = []
        
        # Approximate pricing per 1K tokens (as of 2024, update as needed)
        self._model_pricing: Dict[str, Dict[str, float]] = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
            "gemini-pro": {"prompt": 0.00025, "completion": 0.0005},
        }

    def configure(self, context: Dict[str, Any]):
        """
        Configure tool with session context.
        
        Args:
            context: Dict containing session metadata, may include cost data
        """
        if "session_metadata" in context:
            metadata = context["session_metadata"]
            if "cost_data" in metadata:
                self._cost_history.append(metadata["cost_data"])

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate approximate cost based on model and token usage.
        
        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        pricing = self._model_pricing.get(model, {"prompt": 0.001, "completion": 0.002})
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        return round(prompt_cost + completion_cost, 6)

    def _get_summary_by_model(self, cost_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate cost summary grouped by model.
        
        Args:
            cost_data: List of cost records
            
        Returns:
            Summary dict with totals per model
        """
        summary: Dict[str, Dict[str, Any]] = {}
        
        for record in cost_data:
            model = record.get("model", "unknown")
            if model not in summary:
                summary[model] = {
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_cost_usd": 0.0,
                    "session_count": 0
                }
            
            summary[model]["total_prompt_tokens"] += record.get("prompt_tokens", 0)
            summary[model]["total_completion_tokens"] += record.get("completion_tokens", 0)
            summary[model]["total_cost_usd"] += record.get("cost_usd", 0.0)
            summary[model]["session_count"] += 1
        
        # Round costs
        for model_data in summary.values():
            model_data["total_cost_usd"] = round(model_data["total_cost_usd"], 6)
        
        return summary

    @schema_strict_validator
    def execute(
        self,
        export_format: str = "json",
        output_path: Optional[str] = None,
        session_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute cost export operation.
        
        Args:
            export_format: Output format ('csv' or 'json')
            output_path: File path for export (optional)
            session_data: Session cost data to record (optional)
            
        Returns:
            Export result message with summary or file path
        """
        # If session_data provided, add to history
        if session_data:
            # Calculate cost if not provided
            if "cost_usd" not in session_data:
                model = session_data.get("model", "unknown")
                prompt_tokens = session_data.get("prompt_tokens", 0)
                completion_tokens = session_data.get("completion_tokens", 0)
                session_data["cost_usd"] = self._calculate_cost(model, prompt_tokens, completion_tokens)
            
            self._cost_history.append(session_data)
            
            return f"✅ Cost data recorded for session {session_data.get('session_id', 'unknown')}\n" \
                   f"   Model: {session_data.get('model', 'N/A')}\n" \
                   f"   Tokens: {session_data.get('prompt_tokens', 0)} prompt + {session_data.get('completion_tokens', 0)} completion\n" \
                   f"   Estimated Cost: ${session_data['cost_usd']:.6f}"
        
        # If no data to export, return current history summary
        if not self._cost_history:
            return "ℹ️ No cost data recorded yet. Provide session_data to track costs, or run sessions with cost tracking enabled."
        
        # Generate summary
        summary = self._get_summary_by_model(self._cost_history)
        
        # Prepare export data
        export_data = {
            "total_sessions": len(self._cost_history),
            "total_cost_usd": round(sum(r.get("cost_usd", 0.0) for r in self._cost_history), 6),
            "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in self._cost_history),
            "total_completion_tokens": sum(r.get("completion_tokens", 0) for r in self._cost_history),
            "by_model": summary,
            "sessions": self._cost_history
        }
        
        # Determine output path
        if not output_path:
            output_path = f"session_costs.{export_format}"
        
        # Export to file
        try:
            if export_format == "csv":
                self._export_to_csv(output_path, self._cost_history)
            else:  # json
                self._export_to_json(output_path, export_data)
            
            # Build result message
            result_lines = [
                f"✅ Cost data exported to: {output_path}",
                f"",
                f"📊 Summary:",
                f"   Total Sessions: {export_data['total_sessions']}",
                f"   Total Tokens: {export_data['total_prompt_tokens']} prompt + {export_data['total_completion_tokens']} completion",
                f"   Total Cost: ${export_data['total_cost_usd']:.6f}",
                f"",
                f"💰 Cost by Model:"
            ]
            
            for model, data in summary.items():
                result_lines.append(
                    f"   {model}: ${data['total_cost_usd']:.6f} "
                    f"({data['total_prompt_tokens']}+{data['total_completion_tokens']} tokens, "
                    f"{data['session_count']} sessions)"
                )
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"❌ Error exporting cost data: {str(e)}"

    def _export_to_json(self, path: str, data: Dict[str, Any]):
        """Export data to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _export_to_csv(self, path: str, data: List[Dict[str, Any]]):
        """Export data to CSV file."""
        if not data:
            return
        
        # Define CSV columns
        fieldnames = ["session_id", "model", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd", "timestamp"]
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for record in data:
                # Add calculated total tokens
                record_copy = record.copy()
                record_copy["total_tokens"] = record_copy.get("prompt_tokens", 0) + record_copy.get("completion_tokens", 0)
                writer.writerow(record_copy)

    def get_status_message(self, **kwargs) -> str:
        """Get tool execution status message."""
        export_format = kwargs.get('export_format', 'json')
        output_path = kwargs.get('output_path', 'session_costs.' + export_format)
        return f"\n\n💰 Exporting session cost data to {os.path.basename(output_path)}...\n"
