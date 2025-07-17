from typing import Dict, List, Optional
import logging
import json
from dataclasses import dataclass
from pathlib import Path
import torch
import torch.nn as nn
from micro_os.ai.circuits import LensRefractor
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import time
from dataclasses import asdict

@dataclass
class ContainerSpec:
    base_image: str
    dependencies: List[str]
    environment: Dict[str, str]
    ports: List[int]
    volumes: List[str]
    commands: List[str]
    resource_requirements: Dict[str, float]

class AIContainerManager:
    """
    Manages AI-driven container generation and optimization.
    Uses neural circuits for resource allocation and configuration.
    """
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.lens_refractor = LensRefractor()
        self.template_cache: Dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Base templates for different types of containers
        self.base_templates = {
            "python": self._get_python_template(),
            "node": self._get_node_template(),
            "gpu": self._get_gpu_template()
        }

    def _get_python_template(self) -> str:
        return '''
        FROM python:{{python_version}}
        
        WORKDIR /app
        
        # Install system dependencies
        RUN apt-get update && apt-get install -y {{system_deps}}
        
        # Install Python dependencies
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        
        # Copy application code
        COPY . .
        
        # Environment variables
        {{environment_vars}}
        
        # Expose ports
        {{expose_ports}}
        
        # Command
        CMD {{command}}
        '''

    def _get_node_template(self) -> str:
        return '''
        FROM node:{{node_version}}
        
        WORKDIR /app
        
        # Install dependencies
        COPY package*.json ./
        RUN npm install
        
        # Copy application code
        COPY . .
        
        # Environment variables
        {{environment_vars}}
        
        # Expose ports
        {{expose_ports}}
        
        # Command
        CMD {{command}}
        '''

    def _get_gpu_template(self) -> str:
        return '''
        FROM nvidia/cuda:{{cuda_version}}
        
        WORKDIR /app
        
        # Install system dependencies
        RUN apt-get update && apt-get install -y {{system_deps}}
        
        # Install Python and dependencies
        RUN apt-get install -y python3 python3-pip
        COPY requirements.txt .
        RUN pip3 install --no-cache-dir -r requirements.txt
        
        # Copy application code
        COPY . .
        
        # Environment variables
        {{environment_vars}}
        
        # Expose ports
        {{expose_ports}}
        
        # Command
        CMD {{command}}
        '''

    async def generate_dockerfile(self, spec: ContainerSpec) -> str:
        """Generate a Dockerfile based on container specifications."""
        try:
            # Get base template
            template_type = self._determine_template_type(spec)
            template = self.base_templates[template_type]
            
            # Generate resource configuration using cached neural circuits
            circuit_config = await self._cached_generate_circuit(
                spec.resource_requirements
            )
            
            # Apply resource optimizations
            optimized_spec = self._optimize_spec(spec, circuit_config)
            
            # Fill template
            dockerfile = self._fill_template(template, optimized_spec)
            
            # Cache the generated template
            cache_key = self._generate_cache_key(spec)
            self.template_cache[cache_key] = dockerfile
            
            return dockerfile
        
        except Exception as e:
            self.logger.error(f"Dockerfile generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate Dockerfile: {str(e)}")

    def _determine_template_type(self, spec: ContainerSpec) -> str:
        """Determine which base template to use based on specifications."""
        if "nvidia-cuda" in spec.base_image.lower():
            return "gpu"
        elif "python" in spec.base_image.lower():
            return "python"
        elif "node" in spec.base_image.lower():
            return "node"
        else:
            return "python"  # default to Python template

    def _optimize_spec(self, spec: ContainerSpec, 
                    circuit_config: Dict) -> ContainerSpec:
        """Optimize container specifications based on neural circuit output."""
        resource_mapping = circuit_config["resource_mapping"]
        
        # Apply resource optimizations
        optimized_spec = ContainerSpec(
            base_image=spec.base_image,
            dependencies=self._optimize_dependencies(spec.dependencies),
            environment=spec.environment,
            ports=spec.ports,
            volumes=spec.volumes,
            commands=spec.commands,
            resource_requirements={
                k: resource_mapping.get(k, v)
                for k, v in spec.resource_requirements.items()
            }
        )
        
        return optimized_spec

    def _optimize_dependencies(self, dependencies: List[str]) -> List[str]:
        """Optimize and deduplicate dependencies."""
        # Remove duplicates while preserving order
        seen = set()
        return [
            dep for dep in dependencies
            if not (dep in seen or seen.add(dep))
        ]

    def _fill_template(self, template: str, spec: ContainerSpec) -> str:
        """Fill template with container specifications."""
        replacements = {
            "{{python_version}}": "3.8",  # default Python version
            "{{node_version}}": "14",     # default Node version
            "{{cuda_version}}": "11.0",   # default CUDA version
            "{{system_deps}}": " ".join(spec.dependencies),
            "{{environment_vars}}": self._format_env_vars(spec.environment),
            "{{expose_ports}}": self._format_ports(spec.ports),
            "{{command}}": " && ".join(spec.commands)
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, str(value))
        
        return result.strip()

    def _format_env_vars(self, env_vars: Dict[str, str]) -> str:
        """Format environment variables for Dockerfile."""
        return "\n".join(
            f"ENV {key}={value}"
            for key, value in env_vars.items()
        )

    def _format_ports(self, ports: List[int]) -> str:
        """Format port exposures for Dockerfile."""
        return "\n".join(f"EXPOSE {port}" for port in ports)

    def _generate_cache_key(self, spec: ContainerSpec) -> str:
        """Generate a cache key for the specification."""
        specs = {
            "base_image": spec.base_image,
            "dependencies": sorted(spec.dependencies),
            "environment": spec.environment,
            "ports": sorted(spec.ports),
            "volumes": sorted(spec.volumes),
            "commands": spec.commands,
            "resources": spec.resource_requirements
        }
        return json.dumps(specs, sort_keys=True)

    async def optimize_container(self, container_id: str, 
                            metrics: Dict[str, float]) -> Dict:
        """Optimize container configuration based on runtime metrics."""
        try:
            # Optimize using neural circuits
            optimization_result = await self.lens_refractor.optimize_circuit(
                container_id, metrics
            )
            
            return {
                "container_id": container_id,
                "optimizations": optimization_result["optimized_mapping"],
                "performance_impact": {
                    "loss": optimization_result["loss"],
                    "estimated_improvement": 1.0 - optimization_result["loss"]
                }
            }
        
        except Exception as e:
            self.logger.error(f"Container optimization failed: {str(e)}")
            raise RuntimeError(f"Failed to optimize container: {str(e)}")

    def initialize_neural_mining(self):
        """Initialize neural mining with hashgraph-derived entropy."""
        if not self.blockchain_node.consensus_achieved():
            raise RuntimeError("Cannot initialize mining without consensus")
        
        entropy = self.blockchain_node.hashgraph.get_current_entropy()
        self.neural_entropy = hashlib.sha3_256(entropy).digest()
        self.logger.info("Neural mining initialized with hashgraph entropy")

    @lru_cache(maxsize=100)
    async def _cached_generate_circuit(self, resource_requirements: frozenset) -> Dict:
        """Cached version of lens refractor circuit generation."""
        reqs_dict = dict(resource_requirements)
        start_time = time.perf_counter()

       

        """Generate multiple dockerfiles in parallel."""
        futures = [
            self._executor.submit(
                self.generate_dockerfile,
                spec
            )
            for spec in specs
        ]
        
        results = []
        for future in as_completed(futures):
            try:
                results.append(await future)
            except Exception as e:
                self.logger.error(f"Batch generation failed for one spec: {str(e)}")
                continue
        return results

    async def batch_optimize_containers(self, container_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Dict]:
        """Optimize multiple containers in parallel."""
        futures = {
            self._executor.submit(
                self.optimize_container,
                container_id,
                metrics
            ): container_id
            for container_id, metrics in container_metrics.items()
        }

        results = {}
        for future in as_completed(futures):
            try:
                container_id = futures[future]
                results[container_id] = await future
            except Exception as e:
                self.logger.error(f"Batch optimization failed for container {container_id}: {str(e)}")
        return results
