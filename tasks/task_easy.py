"""
tasks/task_easy.py

Easy task: Stabilization

Environment: Static, no disturbances
Objective: Keep crop healthy by maintaining stable conditions
Challenge: Learn basic control without external perturbations

This is the entry-level task where the agent learns to:
1. Understanding state-action effects
2. Basic feedback control
3. Maintaining crop viability
"""

from env.environment import GreenhouseEasyEnv
from typing import Dict, Any, List


class EasyTask:
    """Easy task: stabilization in static environment."""
    
    def __init__(self, num_episodes: int = 10):
        """
        Initialize easy task.
        
        Args:
            num_episodes: Number of episodes to run
        """
        self.num_episodes = num_episodes
        self.env = GreenhouseEasyEnv()
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
        
        while not done:
            # Agent selects action
            action = agent.select_action(obs)
            
            # Environment step
            obs, reward, terminated, truncated, info = self.env.step(action)
            episode_return += reward
            done = terminated or truncated
        
        result = {
            "episode_return": episode_return,
            "final_crop_health": self.env.state.crop_health,
            "steps": self.env.step_count,
            "success": self.env.state.crop_health > 0.7,
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
            print(f"Easy Task - Episode {ep+1}/{self.num_episodes}: "
                  f"return={result['episode_return']:.2f}, "
                  f"health={result['final_crop_health']:.2f}")
        
        self.episodes = results
        return results
