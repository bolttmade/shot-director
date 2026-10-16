"""Translate comfy-sdk exceptions into friendly EngineErrors (shared by router + workflow adapters)."""

from __future__ import annotations

from .. import errors as E


def _cls(name: str):
    import comfy_sdk
    from comfy_sdk import router_exceptions as rx

    return getattr(comfy_sdk, name, None) or getattr(rx, name, None)


def translate(exc: BaseException) -> E.EngineError:
    """Map an SDK exception to a user-facing error. Unknown exceptions become JobFailed (never raw tracebacks)."""
    if isinstance(exc, E.EngineError):
        return exc
    name = type(exc).__name__
    rid = getattr(exc, "request_id", None)
    suffix = f" (request id {rid})" if rid else ""
    detail = getattr(exc, "detail", None) or str(exc)

    def is_(*names: str) -> bool:
        for n in names:
            c = _cls(n)
            if c is not None and isinstance(exc, c):
                return True
        return name in names

    if is_("InsufficientCredits"):
        return E.InsufficientCredits(
            "Not enough Comfy credits to run this." + suffix,
            hint="Nothing was run and nothing was charged. Top up credits in your Comfy workspace, pick a cheaper engine/model, or switch to Demo mode (no credits needed).",
        )
    if is_("MissingApiKey"):
        return E.Unauthorized("No Comfy API key configured.", hint="Copy .env.example to .env and set COMFY_API_KEY (never commit it), or use the Demo engine.")
    if is_("Unauthorized"):
        return E.Unauthorized("Comfy rejected the API key." + suffix, hint="Check COMFY_API_KEY in your .env, or create a new key in your Comfy workspace.")
    if is_("Forbidden", "NotEnabled"):
        return E.NotConfigured("This account is not enabled for that feature or model." + suffix, hint=f"Details: {detail}. Router/estimates may still be rolling out for your workspace.")
    if is_("QueueFull", "QueueBacklogFull", "RateLimited", "ConcurrencyLimitExceeded"):
        ra = getattr(exc, "retry_after", None)
        return E.QueueFull("Comfy's queue is full or you are rate limited." + suffix, hint=f"Wait {ra or 'a few'} seconds and try again. The app does not auto-retry submits (to avoid double charges).", retryable=True)
    if is_("ContentPolicyViolation"):
        return E.ContentPolicy("The model refused this image or prompt on content-policy grounds." + suffix, hint="Try a different image. Some partner models still charge for refusals; check the model's billing facts.")
    if is_("InvalidWorkflow", "WorkflowFormatUi"):
        return E.JobFailed("The workflow file is not valid API-format JSON." + suffix, hint="Export with 'Save (API Format)' in ComfyUI, or use the files in workflows/.")
    if is_("MissingAsset", "InvalidInput"):
        return E.JobFailed(f"Comfy rejected the request: {detail}" + suffix, hint="This usually means a model/LoRA/node named in the workflow is not installed on that server. See docs/MODELS.md.")
    if is_("JobFailed"):
        err = getattr(exc, "error", None)
        node = getattr(err, "node_id", None)
        msg = getattr(err, "message", None) or str(exc)
        return E.JobFailed(f"The job failed{f' at node {node}' if node else ''}: {msg}"[:400] + suffix, hint="Open the same workflow in ComfyUI to see the node error. Missing models/custom nodes are the usual cause (docs/MODELS.md).")
    if is_("ProviderTimeout", "DeadlineExceeded", "QueueTimeout"):
        return E.JobFailed("The model took too long to answer." + suffix, hint="Nothing is retried automatically. Check your Comfy dashboard before running again; a late result may still be charged.", retryable=True)
    if is_("ProviderError", "InternalError", "ServiceUnavailable"):
        return E.JobFailed(f"The provider reported an error: {detail}"[:300] + suffix, hint="Try again in a minute, or pick another model.", retryable=True)
    if is_("ModelNotFound"):
        return E.NotConfigured(f"Model not found: {detail}" + suffix, hint="Model ids change. Check GET /v2/models or docs/COSTS.md for current ids.")
    code = getattr(exc, "code", None)
    return E.JobFailed(f"{name}: {detail}"[:300] + suffix + (f" [{code}]" if code else ""), hint="See the server log for details.")
