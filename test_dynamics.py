#!/usr/bin/env python
"""Test script to verify environment dynamics are working."""

import numpy as np
from env.environment import GreenhouseEnv

def test_dynamics():
    """Test that environment state evolves over time."""
    
    # Create environment
    env = GreenhouseEnv(max_episode_steps=10)
    obs, info = env.reset()
    
    print('=' * 70)
    print('ENVIRONMENT DYNAMICS TEST')
    print('=' * 70)
    print('\n=== STEP 0 (Initial State) ===')
    print(f'Temperature: {obs[0]:.2f}°C')
    print(f'Humidity: {obs[1]:.2f}%')
    print(f'CO2: {obs[2]:.1f} ppm')
    print(f'Light: {obs[3]:.1f} µmol/m²/s')
    print(f'Water: {obs[4]:.1f} units')
    print(f'Energy: {obs[5]:.1f} units')
    print(f'Health: {obs[6]:.3f}')
    print(f'Mold: {obs[7]:.3f}')
    
    # Store initial state for comparison
    initial_obs = obs.copy()
    
    # Take a few steps with an action
    action = np.array([0.5, 0.0, 0.2, 0.0, 0.1, 0.5, 0.0, 0.0], dtype=np.float32)
    
    print('\n' + '=' * 70)
    print('ACTION: [heating=0.5, humidify=0.2, ventilation=0.1, irrigation=0.5]')
    print('=' * 70)
    
    total_reward = 0.0
    for step in range(1, 6):
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        print(f'\n--- STEP {step} ---')
        print(f'Temperature: {obs[0]:7.2f}°C (Δ: {obs[0] - initial_obs[0]:+.2f})')
        print(f'Humidity:    {obs[1]:7.2f}% (Δ: {obs[1] - initial_obs[1]:+.2f})')
        print(f'CO2:         {obs[2]:7.1f} ppm (Δ: {obs[2] - initial_obs[2]:+.1f})')
        print(f'Light:       {obs[3]:7.1f} µmol/m²/s')
        print(f'Water:       {obs[4]:7.1f} units (Δ: {obs[4] - initial_obs[4]:+.1f})')
        print(f'Energy:      {obs[5]:7.1f} units (Δ: {obs[5] - initial_obs[5]:+.1f})')
        print(f'Health:      {obs[6]:7.3f} (Δ: {obs[6] - initial_obs[6]:+.3f})')
        print(f'Mold:        {obs[7]:7.3f} (Δ: {obs[7] - initial_obs[7]:+.3f})')
        print(f'Reward:      {reward:7.3f} (Cumulative: {total_reward:.3f})')
        
        if terminated:
            print(f'[EPISODE ENDED: Crop died]')
            break
        if truncated:
            print(f'[Truncated: Max steps reached]')
            break
    
    # Verify changes occurred
    print('\n' + '=' * 70)
    print('VERIFICATION')
    print('=' * 70)
    
    changes = {
        'Temperature': abs(obs[0] - initial_obs[0]),
        'Humidity': abs(obs[1] - initial_obs[1]),
        'CO2': abs(obs[2] - initial_obs[2]),
        'Water': abs(obs[4] - initial_obs[4]),
        'Energy': abs(obs[5] - initial_obs[5]),
        'Health': abs(obs[6] - initial_obs[6]),
    }
    
    print('\nNote: Some variables may change very slightly depending on time of day and conditions.')
    print('Confirm that at least some variables changed:\n')
    
    any_changed = False
    for var, change in changes.items():
        if change > 0.01:
            print(f'✅ {var:12s}: Changed by {change:7.2f}')
            any_changed = True
        else:
            print(f'   {var:12s}: Changed by {change:7.6f} (negligible)')
    
    print(f'\n💰 Total Reward: {total_reward:.3f}')
    print(f'   (Should be non-constant if dynamics are working)')
    
    if any_changed:
        print('\n✅ SUCCESS: Environment is EVOLVING!')
        print('   State variables are changing based on actions and time.')
    else:
        print('\n❌ FAILURE: Environment is NOT evolving!')
        print('   No significant state changes detected.')
    
    return any_changed

if __name__ == "__main__":
    success = test_dynamics()
    exit(0 if success else 1)
