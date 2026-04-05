"""
inference.py

Agent inference and interaction layer.
Connects LLM/RL agent to the greenhouse environment.
Handles:
- Environment initialization
- Episode orchestration
- Task execution
- Result aggregation and evaluation
"""

from typing import Optional
import numpy as np

from env.environment import GreenhouseEnv, GreenhouseEasyEnv, GreenhouseMediumEnv, GreenhouseHardEnv
from tasks.task_easy import EasyTask
from tasks.task_medium import MediumTask
from tasks.task_hard import HardTask
from tasks.graders import (
    grade_easy_task,
    grade_medium_task,
    grade_hard_task,
    grade_overall_performance,
    print_grading_report,
)


class GreenhouseAgent:
    """
    Base agent interface for greenhouse control.
    Subclass and implement select_action() for specific agent types.
    """
    
    def select_action(self, observation: np.ndarray) -> np.ndarray:
        """
        Select action given observation from environment.
        
        Args:
            observation: Observation array from environment
            
        Returns:
            Action array [0, 1]^8
        """
        raise NotImplementedError
    
    def reset(self):
        """Reset agent state (if needed)."""
        pass


class RandomAgent(GreenhouseAgent):
    """Agent that takes random actions (baseline)."""
    
    def select_action(self, observation: np.ndarray) -> np.ndarray:
        """Return random action."""
        return np.random.uniform(0, 1, 8).astype(np.float32)


class GreenhouseInference:
    """
    Main inference orchestrator.
    Runs agent through all three tasks and generates grading report.
    """
    
    def __init__(self, agent: GreenhouseAgent):
        """
        Initialize inference runner.
        
        Args:
            agent: Agent instance to evaluate
        """
        self.agent = agent
        self.easy_results = []
        self.medium_results = []
        self.hard_results = []
    
    def run_all_tasks(self) -> dict:
        """
        Run agent through all three tasks.
        
        Returns:
            Dictionary with scores and results
        """
        print("\n" + "="*60)
        print("STARTING GREENHOUSE ENVIRONMENT EVALUATION")
        print("="*60)
        
        # Easy task
        print("\n[EASY TASK] Running 10 episodes (stabilization)...")
        easy_task = EasyTask(num_episodes=10)
        self.easy_results = easy_task.run(self.agent)
        easy_score = grade_easy_task(self.easy_results)
        print(f"Easy Task Score: {easy_score:.3f}\n")
        
        # Medium task
        print("[MEDIUM TASK] Running 20 episodes (adaptation)...")
        medium_task = MediumTask(num_episodes=20)
        self.medium_results = medium_task.run(self.agent)
        medium_score = grade_medium_task(self.medium_results)
        print(f"Medium Task Score: {medium_score:.3f}\n")
        
        # Hard task
        print("[HARD TASK] Running 30 episodes (optimization)...")
        hard_task = HardTask(num_episodes=30)
        self.hard_results = hard_task.run(self.agent)
        hard_score = grade_hard_task(self.hard_results)
        print(f"Hard Task Score: {hard_score:.3f}\n")
        
        # Overall
        overall_score = grade_overall_performance(easy_score, medium_score, hard_score)
        print_grading_report(easy_score, medium_score, hard_score, overall_score)
        
        return {
            "easy_score": easy_score,
            "medium_score": medium_score,
            "hard_score": hard_score,
            "overall_score": overall_score,
            "easy_results": self.easy_results,
            "medium_results": self.medium_results,
            "hard_results": self.hard_results,
        }
    
    def run_single_episode(
        self,
        difficulty: str = "easy"
    ) -> dict:
        """
        Run single episode at specified difficulty.
        
        Args:
            difficulty: "easy", "medium", or "hard"
            
        Returns:
            Episode result dictionary
        """
        if difficulty == "easy":
            env = GreenhouseEasyEnv()
        elif difficulty == "medium":
            env = GreenhouseMediumEnv()
        elif difficulty == "hard":
            env = GreenhouseHardEnv()
        else:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        
        obs, info = env.reset()
        done = False
        episode_return = 0.0
        steps = 0
        
        while not done:
            action = self.agent.select_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_return += reward
            done = terminated or truncated
            steps += 1
        
        return {
            "difficulty": difficulty,
            "episode_return": episode_return,
            "final_crop_health": env.state.crop_health,
            "steps": steps,
        }


def main():
    """
    Main entry point for greenhouse evaluation.
    Example: Run random agent baseline.
    """
    print("Initializing greenhouse environment...")
    
    # Create agent (replace with actual agent)
    agent = RandomAgent()
    
    # Run evaluation
    inference = GreenhouseInference(agent)
    results = inference.run_all_tasks()
    
    # Print summary
    print("\nFinal Summary:")
    print(f"  Overall Score: {results['overall_score']:.3f}")
    print(f"  Easy Score: {results['easy_score']:.3f}")
    print(f"  Medium Score: {results['medium_score']:.3f}")
    print(f"  Hard Score: {results['hard_score']:.3f}")


if __name__ == "__main__":
    main()
