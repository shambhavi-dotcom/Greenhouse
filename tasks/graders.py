"""
tasks/graders.py

Grading logic for evaluating agent performance.
Converts episode results and task performance into 0.0-1.0 scores.

Grading criteria:
- Crop survival and health
- Resource efficiency
- Stability of decisions
- Performance across task difficulties
"""

from typing import Dict, List, Any
import numpy as np


def grade_easy_task(results: List[Dict[str, Any]]) -> float:
    """
    Grade performance on easy task.
    
    Criteria:
        - crop_health_final > 0.7 in most episodes (70%)
        - Consistency across episodes (20%)
        - Zero catastrophic failures (10%)
    
    Args:
        results: List of episode results from EasyTask.run()
        
    Returns:
        Score 0.0-1.0
    """
    if not results:
        return 0.0
    
    # Extract metrics
    final_healths = [r["final_crop_health"] for r in results]
    successes = [r["success"] for r in results]
    
    # Score components
    health_score = np.mean([min(h / 0.7, 1.0) for h in final_healths])  # 0.0-1.0
    success_rate = np.mean(successes)  # 0.0-1.0
    consistency = 1.0 - np.std(final_healths) / (max(final_healths) - min(final_healths) + 1e-6)
    
    # Weighted combination
    total_score = (
        0.60 * health_score +
        0.30 * success_rate +
        0.10 * consistency
    )
    
    return float(np.clip(total_score, 0.0, 1.0))


def grade_medium_task(results: List[Dict[str, Any]]) -> float:
    """
    Grade performance on medium task.
    
    Criteria:
        - crop_health_final > 0.6 (50%)
        - Adaptation to disturbances (30%)
        - Success rate > 50% (20%)
    
    Args:
        results: List of episode results from MediumTask.run()
        
    Returns:
        Score 0.0-1.0
    """
    if not results:
        return 0.0
    
    # Extract metrics
    final_healths = [r["final_crop_health"] for r in results]
    successes = [r["success"] for r in results]
    max_disturbances = [r.get("max_weather_disturbance", 0.0) for r in results]
    
    # Score components
    health_score = np.mean([min(h / 0.6, 1.0) for h in final_healths])
    success_rate = np.mean(successes)
    
    # Adaptation: maintain health despite disturbances
    adaptation_score = 1.0
    if max_disturbances and max(max_disturbances) > 0:
        # If large disturbances occur but health maintained, high adaptation score
        avg_disturbance = np.mean(max_disturbances)
        disturbance_impact = avg_disturbance / 10.0  # Normalize
        avg_health = np.mean(final_healths)
        adaptation_score = max(0.0, 1.0 - (disturbance_impact * 0.5 - avg_health * 0.5))
    
    # Weighted combination
    total_score = (
        0.50 * health_score +
        0.30 * adaptation_score +
        0.20 * success_rate
    )
    
    return float(np.clip(total_score, 0.0, 1.0))


def grade_hard_task(results: List[Dict[str, Any]]) -> float:
    """
    Grade performance on hard task.
    
    Criteria:
        - Crop health > 0.5 (40%)
        - Resource efficiency (40%)
        - Planning & optimization (20%)
    
    Args:
        results: List of episode results from HardTask.run()
        
    Returns:
        Score 0.0-1.0
    """
    if not results:
        return 0.0
    
    # Extract metrics
    final_healths = [r["final_crop_health"] for r in results]
    efficiencies = [r["resource_efficiency"] for r in results]
    successes = [r["success"] for r in results]
    
    # Score components
    health_score = np.mean([min(h / 0.5, 1.0) for h in final_healths])
    efficiency_score = np.mean([min(e / 0.02, 1.0) for e in efficiencies])  # Normalize to 0.02 threshold
    success_rate = np.mean(successes)
    
    # Weighted combination
    total_score = (
        0.40 * health_score +
        0.40 * efficiency_score +
        0.20 * success_rate
    )
    
    return float(np.clip(total_score, 0.0, 1.0))


def grade_overall_performance(
    easy_score: float,
    medium_score: float,
    hard_score: float,
) -> float:
    """
    Compute overall performance score across all tasks.
    
    Args:
        easy_score: Score on easy task (0.0-1.0)
        medium_score: Score on medium task (0.0-1.0)
        hard_score: Score on hard task (0.0-1.0)
        
    Returns:
        Overall score 0.0-1.0
    """
    # Equally weighted across difficulties
    overall = (easy_score + medium_score + hard_score) / 3.0
    
    # Small bonus if all tasks > 0.5
    if easy_score > 0.5 and medium_score > 0.5 and hard_score > 0.5:
        overall *= 1.05
    
    return float(np.clip(overall, 0.0, 1.0))


def print_grading_report(
    easy_score: float,
    medium_score: float,
    hard_score: float,
    overall_score: float,
):
    """
    Print a formatted grading report.
    
    Args:
        easy_score: Score on easy task
        medium_score: Score on medium task
        hard_score: Score on hard task
        overall_score: Overall combined score
    """
    print("\n" + "="*60)
    print("GREENHOUSE TASK GRADING REPORT")
    print("="*60)
    print(f"Easy Task (Stabilization):      {easy_score:.3f}")
    print(f"Medium Task (Adaptation):       {medium_score:.3f}")
    print(f"Hard Task (Optimization):       {hard_score:.3f}")
    print("-"*60)
    print(f"OVERALL SCORE:                  {overall_score:.3f}")
    print("="*60)
