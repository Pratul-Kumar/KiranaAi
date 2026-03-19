import os
import logging

try:
    import mlflow
    MLFLOW_ENABLED = True
except ImportError:
    MLFLOW_ENABLED = False

logger = logging.getLogger(__name__)

def setup_experiment_tracking(experiment_name: str = "kirana_ai_experiments"):
    """Initialize MLflow experiment tracking."""
    if not MLFLOW_ENABLED:
        logger.warning("MLflow is not installed. Experiment tracking is disabled.")
        return
    
    # MLflow URI setup
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(mlflow_uri)
    
    # Set experiment
    mlflow.set_experiment(experiment_name)
    logger.info(f"MLflow experiment '{experiment_name}' initialized.")

def log_experiment_params(params: dict):
    """Log parameters (hyperparameters or config values) for the current run."""
    if MLFLOW_ENABLED:
        mlflow.log_params(params)

def log_experiment_metrics(metrics: dict):
    """Log evaluation metrics for the current run."""
    if MLFLOW_ENABLED:
        mlflow.log_metrics(metrics)
