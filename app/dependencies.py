import services.fitdit_service as fitdit_service


def get_fitdit_service():
    return fitdit_service


def init_service():
    print(f"[init] FitDiT target: {fitdit_service._get_base_url()}")
    print("[init] Skipping local model load — using Colab HTTP backend")