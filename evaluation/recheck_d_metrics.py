"""Independent recorded D arithmetic: no model, engine or scorer imports."""
import json

from recheck_c_metrics import recheck

if __name__ == "__main__":
    print(json.dumps(recheck(("d_extraction_baseline", "d_extraction_final",
                              "d_qwen_baseline", "d_qwen_final")), indent=2))
