"""
Monitoring and System Health Module

This module provides comprehensive monitoring, health checks, and system metrics
for the Java Version Fixer application.
"""

import time
import psutil
import logging
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

from core.error_handling import ErrorHandler, ErrorCategory, ErrorSeverity, get_error_handler


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for individual system components."""
    name: str
    status: HealthStatus
    last_check: datetime
    response_time: Optional[float] = None
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System performance and resource metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_processes: int
    docker_containers: int = 0
    api_calls_per_minute: int = 0
    error_rate: float = 0.0
    average_response_time: float = 0.0


class SystemMonitor:
    """
    Comprehensive system monitoring and health checking.
    
    Monitors system resources, component health, and provides
    alerts and recommendations for system optimization.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize system monitor.
        
        Args:
            check_interval: Health check interval in seconds
        """
        self.error_handler = get_error_handler()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.check_interval = check_interval
        
        # Component health tracking
        self.component_health: Dict[str, ComponentHealth] = {}
        self.system_metrics: List[SystemMetrics] = []
        self.max_metrics_history = 1000  # Keep last 1000 metrics
        
        # Performance tracking
        self.api_call_times: List[float] = []
        self.docker_operation_times: List[float] = []
        self.last_health_check = datetime.now()
        
        # Initialize component monitoring
        self._initialize_component_monitoring()
    
    def _initialize_component_monitoring(self):
        """Initialize monitoring for system components."""
        components = [
            "docker_manager",
            "llm_agent", 
            "error_classifier",
            "validation_system",
            "java_runner"
        ]
        
        for component in components:
            self.component_health[component] = ComponentHealth(
                name=component,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.now()
            )
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Returns:
            Dictionary with complete health status and metrics
        """
        try:
            # Collect system metrics
            metrics = self._collect_system_metrics()
            self.system_metrics.append(metrics)
            
            # Trim metrics history
            if len(self.system_metrics) > self.max_metrics_history:
                self.system_metrics = self.system_metrics[-self.max_metrics_history:]
            
            # Check component health
            self._check_component_health()
            
            # Calculate overall health
            overall_health = self._calculate_overall_health()
            
            # Generate health report
            health_report = {
                "overall_status": overall_health,
                "timestamp": datetime.now().isoformat(),
                "system_metrics": {
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "disk_usage": metrics.disk_usage,
                    "active_processes": metrics.active_processes,
                    "docker_containers": metrics.docker_containers
                },
                "component_health": {
                    name: {
                        "status": health.status.value,
                        "last_check": health.last_check.isoformat(),
                        "response_time": health.response_time,
                        "error_count": health.error_count,
                        "last_error": health.last_error
                    }
                    for name, health in self.component_health.items()
                },
                "performance_metrics": {
                    "average_api_response_time": self._calculate_average_response_time(self.api_call_times),
                    "average_docker_response_time": self._calculate_average_response_time(self.docker_operation_times),
                    "error_rate": self._calculate_error_rate(),
                    "api_calls_per_minute": len([t for t in self.api_call_times if time.time() - t < 60])
                },
                "recommendations": self._generate_recommendations(metrics, overall_health)
            }
            
            self.last_health_check = datetime.now()
            return health_report
            
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="SystemMonitor",
                operation="check_system_health",
                user_message="System health check failed."
            )
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # Process count
            active_processes = len(psutil.pids())
            
            # Docker containers (if available)
            docker_containers = self._count_docker_containers()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                active_processes=active_processes,
                docker_containers=docker_containers,
                api_calls_per_minute=len([t for t in self.api_call_times if time.time() - t < 60]),
                error_rate=self._calculate_error_rate(),
                average_response_time=self._calculate_average_response_time(self.api_call_times)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_processes=0
            )
    
    def _count_docker_containers(self) -> int:
        """Count active Docker containers."""
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()
            return len(containers)
        except Exception:
            return 0
    
    def _check_component_health(self):
        """Check health of individual system components."""
        # Docker Manager health check
        self._check_docker_health()
        
        # LLM Agent health check
        self._check_llm_health()
        
        # Other components can be added here
        
    def _check_docker_health(self):
        """Check Docker service health."""
        start_time = time.time()
        try:
            import docker
            client = docker.from_env()
            client.ping()
            
            response_time = time.time() - start_time
            self.component_health["docker_manager"] = ComponentHealth(
                name="docker_manager",
                status=HealthStatus.HEALTHY,
                last_check=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            self.component_health["docker_manager"] = ComponentHealth(
                name="docker_manager",
                status=HealthStatus.CRITICAL,
                last_check=datetime.now(),
                last_error=str(e),
                error_count=self.component_health.get("docker_manager", ComponentHealth("docker_manager", HealthStatus.UNKNOWN, datetime.now())).error_count + 1
            )
    
    def _check_llm_health(self):
        """Check LLM service health."""
        try:
            # This would need to be integrated with the actual LLM agent
            # For now, we'll do a basic check
            self.component_health["llm_agent"] = ComponentHealth(
                name="llm_agent",
                status=HealthStatus.HEALTHY,
                last_check=datetime.now()
            )
        except Exception as e:
            self.component_health["llm_agent"] = ComponentHealth(
                name="llm_agent",
                status=HealthStatus.DEGRADED,
                last_check=datetime.now(),
                last_error=str(e)
            )
    
    def _calculate_overall_health(self) -> HealthStatus:
        """Calculate overall system health based on component health."""
        if not self.component_health:
            return HealthStatus.UNKNOWN
        
        critical_count = sum(1 for h in self.component_health.values() if h.status == HealthStatus.CRITICAL)
        degraded_count = sum(1 for h in self.component_health.values() if h.status == HealthStatus.DEGRADED)
        healthy_count = sum(1 for h in self.component_health.values() if h.status == HealthStatus.HEALTHY)
        
        total_components = len(self.component_health)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif degraded_count > total_components // 2:
            return HealthStatus.CRITICAL
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        elif healthy_count == total_components:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def _calculate_average_response_time(self, response_times: List[float]) -> float:
        """Calculate average response time from recent measurements."""
        if not response_times:
            return 0.0
        
        # Only consider recent measurements (last 5 minutes)
        recent_times = [t for t in response_times if time.time() - t < 300]
        return sum(recent_times) / len(recent_times) if recent_times else 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate based on recent activity."""
        # This would need to be integrated with the error handler
        # For now, return a placeholder
        return 0.0
    
    def _generate_recommendations(self, metrics: SystemMetrics, overall_health: HealthStatus) -> List[str]:
        """Generate system optimization recommendations."""
        recommendations = []
        
        # CPU usage recommendations
        if metrics.cpu_usage > 80:
            recommendations.append("High CPU usage detected. Consider reducing concurrent operations.")
        
        # Memory usage recommendations
        if metrics.memory_usage > 85:
            recommendations.append("High memory usage detected. Consider restarting the application.")
        
        # Disk usage recommendations
        if metrics.disk_usage > 90:
            recommendations.append("Low disk space. Consider cleaning up temporary files.")
        
        # Component-specific recommendations
        for name, health in self.component_health.items():
            if health.status == HealthStatus.CRITICAL:
                if name == "docker_manager":
                    recommendations.append("Docker service is not available. Please start Docker.")
                elif name == "llm_agent":
                    recommendations.append("LLM service is not available. Check API keys and connectivity.")
            elif health.status == HealthStatus.DEGRADED:
                recommendations.append(f"{name} is experiencing issues. Monitor for stability.")
        
        # Performance recommendations
        if metrics.average_response_time > 5.0:
            recommendations.append("Slow response times detected. Check network connectivity and system load.")
        
        if not recommendations:
            recommendations.append("System is operating normally.")
        
        return recommendations
    
    def record_api_call(self, response_time: float):
        """Record API call timing for performance monitoring."""
        current_time = time.time()
        self.api_call_times.append(current_time)
        
        # Keep only recent measurements (last 10 minutes)
        cutoff_time = current_time - 600
        self.api_call_times = [t for t in self.api_call_times if t > cutoff_time]
    
    def record_docker_operation(self, response_time: float):
        """Record Docker operation timing for performance monitoring."""
        current_time = time.time()
        self.docker_operation_times.append(current_time)
        
        # Keep only recent measurements (last 10 minutes)
        cutoff_time = current_time - 600
        self.docker_operation_times = [t for t in self.docker_operation_times if t > cutoff_time]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a quick health summary for display."""
        overall_health = self._calculate_overall_health()
        
        healthy_components = sum(1 for h in self.component_health.values() if h.status == HealthStatus.HEALTHY)
        total_components = len(self.component_health)
        
        latest_metrics = self.system_metrics[-1] if self.system_metrics else None
        
        return {
            "overall_status": overall_health.value,
            "healthy_components": healthy_components,
            "total_components": total_components,
            "health_percentage": (healthy_components / total_components * 100) if total_components > 0 else 0,
            "last_check": self.last_health_check.isoformat(),
            "system_load": {
                "cpu": latest_metrics.cpu_usage if latest_metrics else 0,
                "memory": latest_metrics.memory_usage if latest_metrics else 0,
                "disk": latest_metrics.disk_usage if latest_metrics else 0
            } if latest_metrics else None
        }
    
    def export_health_report(self, file_path: str):
        """Export detailed health report to file."""
        try:
            health_report = self.check_system_health()
            
            with open(file_path, 'w') as f:
                json.dump(health_report, f, indent=2, default=str)
            
            self.logger.info(f"Health report exported to {file_path}")
            
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.LOW,
                component="SystemMonitor",
                operation="export_health_report",
                user_message="Failed to export health report."
            )


# Global system monitor instance
_global_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """Get or create global system monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor()
    return _global_monitor