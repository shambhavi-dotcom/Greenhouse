"""
tasks/task_medium.py

Medium task: Adaptation

Environment: Weather disturbances, changing conditions
Objective: Maintain crop health while adapting to external changes
Challenge: Requires reactive control and real-time adaptation

This task introduces:
1. External weather changes
2. Non-stationary environment
3. Reactive decision-making
4. Resource constraints
"""

from env.environment import GreenhouseMediumEnv
from typing import Dict, Any, List


class MediumTask:
    """Medium task: adaptation to changing environment."""
    
    def __init__(self, num_episodes: int = 20):
        """
        Initialize medium task.
        
        Args:
            num_episodes: Number of episodes to run
        """
        self.num_episodes = num_episodes
        self.env = GreenhouseMediumEnv()
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
        max_weather_disturbance = 0.0
        
        while not done:
            # Agent selects action
            action = agent.select_action(obs)
            
            # Environment step
            obs, reward, terminated, truncated, info = self.env.step(action)
            episode_return += reward
            done = terminated or truncated
            
            # Track external disturbances
            if hasattr(self.env.state, 'external_weather'):
                disturbance = abs(self.env.state.external_weather.get("temp_shift", 0.0))
                max_weather_disturbance = max(max_weather_disturbance, disturbance)
        
        result = {
            "episode_return": episode_return,
            "final_crop_health": self.env.state.crop_health,
            "steps": self.env.step_count,
            "success": self.env.state.crop_health > 0.6,
            "max_weather_disturbance": max_weather_disturbance,
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
            print(f"Medium Task - Episode {ep+1}/{self.num_episodes}: "
                  f"return={result['episode_return']:.2f}, "
                  f"health={result['final_crop_health']:.2f}, "
                  f"disturbance={result['max_weather_disturbance']:.2f}")
        
        self.episodes = results
        return results
