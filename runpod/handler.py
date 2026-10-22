"""
RunPod handler — 本项目**当前版本未使用**。
------------------------------------------------------------
保留这个文件是为了说明"我们评估过 RunPod，并明确记录为什么没用"，
而不是留一个空壳假装用了。

Domain 2 的方案里，文案起草走 LLM API（一次几百 token），
没有训练、没有微调、没有 GPU 推理的需求 —— 按 Participant
Handbook 9.3，这种情况**不强制**使用 RunPod。

如果后续要自己托管模型（例如本地跑一个分类器判断"这个客户值不值得
升级催收"），就把这个 handler 补成真正的推理逻辑，部署成
RunPod Serverless Endpoint，然后在 Tech Declaration 里贴截图
（必须含 endpoint URL / GPU 型号 / 运行时长）。

申报书里必须写清楚：Not used in current prototype — no GPU workload。
"""
import os
import time


def handler(job):
    """
    RunPod serverless 标准入口签名。
    当前是占位实现，返回明确的"未启用"而不是假装有结果。
    """
    started = time.time()
    return {
        "status": "not_implemented",
        "message": ("CollectLoop runs its drafting step through an LLM API, "
                    "so no GPU workload exists in this prototype."),
        "gpu_type": os.environ.get("RUNPOD_GPU_TYPE", "n/a"),
        "runtime_sec": round(time.time() - started, 3),
    }


if __name__ == "__main__":
    print("This handler is a placeholder. See module docstring.")
