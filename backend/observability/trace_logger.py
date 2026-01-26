"""
Trace Logger: Custom observability system for agent decisions.
Logs all agent actions to JSONL file for full auditability.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


class TraceLogger:
    """
    Custom trace logger for agent observability.
    Stores traces in newline-delimited JSON format.
    """
    
    def __init__(self, log_file: str = None):
        """
        Initialize trace logger.
        
        Args:
            log_file: Path to trace log file (defaults to data/traces.jsonl)
        """
        if log_file is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            log_file = base_dir / "data" / "traces.jsonl"
        
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True, parents=True)
        
        # Create file if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch()
    
    def log_trace(self, trace_id: str, agent_name: str, action: str,
                  input_data: Dict, output_data: Dict, decision_reason: str,
                  status: str = "success") -> str:
        """
        Log a single agent action trace.
        
        Args:
            trace_id: UUID for grouping related actions
            agent_name: Name of the agent performing action
            action: Action being performed
            input_data: Input parameters to the action
            output_data: Output/result of the action
            decision_reason: Human-readable explanation of decision
            status: "success", "failed", or "error"
        
        Returns:
            trace_id
        """
        
        trace = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "action": action,
            "input": input_data,
            "output": output_data,
            "decision_reason": decision_reason,
            "status": status
        }
        
        # Append to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(trace) + '\n')
        
        return trace_id
    
    def get_traces(self, limit: int = 100, trace_id: str = None,
                   agent_name: str = None) -> List[Dict]:
        """
        Retrieve traces with optional filtering.
        
        Args:
            limit: Maximum number of traces to return
            trace_id: Filter by specific trace ID
            agent_name: Filter by agent name
        
        Returns:
            List of trace dictionaries
        """
        
        if not self.log_file.exists():
            return []
        
        traces = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        trace = json.loads(line)
                        
                        # Apply filters
                        if trace_id and trace.get('trace_id') != trace_id:
                            continue
                        if agent_name and trace.get('agent_name') != agent_name:
                            continue
                        
                        traces.append(trace)
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent traces first
        traces.reverse()
        
        return traces[:limit]
    
    def get_trace_by_id(self, trace_id: str) -> List[Dict]:
        """Get all actions for a specific trace ID."""
        return self.get_traces(limit=1000, trace_id=trace_id)
    
    def get_recent_traces_grouped(self, limit: int = 50) -> List[Dict]:
        """
        Get recent traces grouped by trace_id.
        Useful for displaying complete workflows.
        
        Returns:
            List of grouped traces with metadata
        """
        
        all_traces = self.get_traces(limit=limit * 10)  # Get more to ensure we have complete groups
        
        # Group by trace_id
        grouped = {}
        for trace in all_traces:
            tid = trace['trace_id']
            if tid not in grouped:
                grouped[tid] = {
                    'trace_id': tid,
                    'start_time': trace['timestamp'],
                    'actions': []
                }
            grouped[tid]['actions'].append(trace)
        
        # Convert to list and sort by start time
        result = list(grouped.values())
        result.sort(key=lambda x: x['start_time'], reverse=True)
        
        return result[:limit]
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about agent activity.
        
        Returns:
            Dictionary with agent performance metrics
        """
        
        all_traces = self.get_traces(limit=10000)
        
        stats = {
            "total_traces": len(all_traces),
            "by_agent": {},
            "by_status": {"success": 0, "failed": 0, "error": 0},
            "recent_activity": []
        }
        
        for trace in all_traces:
            agent = trace.get('agent_name', 'unknown')
            status = trace.get('status', 'unknown')
            
            # Count by agent
            if agent not in stats['by_agent']:
                stats['by_agent'][agent] = 0
            stats['by_agent'][agent] += 1
            
            # Count by status
            if status in stats['by_status']:
                stats['by_status'][status] += 1
        
        # Get recent activity (last 10)
        stats['recent_activity'] = all_traces[:10]
        
        return stats
    
    def clear_logs(self):
        """Clear all trace logs. Use with caution!"""
        if self.log_file.exists():
            self.log_file.unlink()
            self.log_file.touch()
