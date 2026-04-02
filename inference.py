# inference.py

from support_env import CustomerSupportEnv

# Initialize environment
env = CustomerSupportEnv(task_id="easy", seed=42)

def run():
    """
    Dummy inference entry point required for validation.
    """
    obs = env.reset()
    return {
        "message": "Inference setup successful",
        "initial_observation": obs.model_dump()
    }


if __name__ == "__main__":
    print(run())