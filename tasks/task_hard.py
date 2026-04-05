"""
tasks/task_hard.py

Hard task: Optimization

Environment: Limited resources, weather disturbances, all constraints active
Objective: Maximize crop health AND optimize resource usage
Challenge: Requires planning, resource allocation, and multi-objective optimization

This is the most challenging task with:
1. Strict energy budget
2. Limited water supply
3. Weather unpredictability
4. Trade-offs between objectives
5. Long episode horizon (planning required)
"""

from env.environment import GreenhouseHardEnv
from typing import Dict, Any, List


class HardTask:
    """Hard task: optimization under resource constraints."""
    
    def __init__(self, num_episodes: int = 30):
        """
        Initialize hard task.
        
        Args:
            num_episodes: Number of episodes to run
        """
        self.num_episodes = num_episodes
        self.env = GreenhouseHardEnv()
        self.episodes = []
    
    def run_episode(self, agent) -> Dict[str, Any]:
        """
        Run single episode with given agent.
        
        Args:
            agent: Agent that takes observations and returns actions
            
        Returns:
            Episode result dictionary
        """
        obs, info = self.env.reset()
        done = False
        episode_return = 0.0
        total_energy_used = 0.0
        total_water_used = 0.0
        
        while not done:
            # Agent selects action
            action = agent.select_action(obs)
            
            # Environment step
            obs, reward, terminated, truncated, info = self.env.step(action)
            episode_return += reward
            done = terminated or truncated
            
            # Track resource usage
            if "action_info" in info:
                total_energy_used += info["action_info"].get("energy_used", 0.0)
                total_water_used += info["action_info"].get("water_used", 0.0)
        
        # Compute resource efficiency
        efficiency = 0.0
        if total_energy_used > 0 or total_water_used > 0:
            if self.env.state.crop_health > 0.5:
                efficiency = self.env.state.crop_health / (total_energy_used + total_water_used + 1e-6)
        
        result = {
            "episode_return": episode_return,
            "final_crop_health": self.env.state.crop_health,
            "steps": self.env.step_count,
            "total_energy_used": total_energy_used,
            "total_water_used": total_water_used,
            "resource_efficiency": efficiency,
            "success": (self.env.state.crop_health > 0.5) and efficiency > 0.01,
        }
        
        return result
    
    def run(self, agent) -> List[Dict[str, Any]]:
        """
        Run all episodes of this task.
        
        Args:
            agent: Agent to evaluate
            
        Returns:
            List of episode results
        """
        results = []
        for ep in range(self.num_episodes):
            result = self.run_episode(agent)
            results.append(result)
            print(f"Hard Task - Episode {ep+1}/{self.num_episodes}: "
                  f"return={result['episode_return']:.2f}, "
                  f"health={result['final_crop_health']:.2f}, "
                  f"efficiency={result['resource_efficiency']:.3f}")
        
        self.episodes = results
        return results
