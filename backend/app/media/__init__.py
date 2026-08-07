"""L.U.C.E.R.O multimodal media OS (Replicate + print + Tavily + jobs)."""

__all__ = ["JobService"]


def __getattr__(name: str):
    if name == "JobService":
        from app.media.job_service import JobService

        return JobService
    raise AttributeError(name)
