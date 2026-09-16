"""End-to-end campaign skeleton: diffuse -> sequence -> validate -> filter.

Only the first stage is wired up; the rest are explicit stubs so the shape
of the pipeline is visible from the start.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_design.runner import DesignRequest, run_design  # noqa: E402


def stage_diffuse(spec: dict) -> dict:
    return run_design(DesignRequest(**spec))


def stage_sequence(diffusion_result: dict) -> dict:
    """ProteinMPNN over the generated backbones. CPU-friendly."""
    raise NotImplementedError("wire up ProteinMPNN here")


def stage_validate(sequence_result: dict) -> dict:
    """Refold with ESMFold/AF2 and compare to the designed backbone."""
    raise NotImplementedError("wire up structure prediction here")


def stage_filter(validation_result: dict, rmsd_cutoff: float = 2.0) -> list:
    """Keep designs that refold to what was designed."""
    raise NotImplementedError("define acceptance criteria here")


if __name__ == "__main__":
    print(stage_diffuse({"name": "smoke", "contigs": "[40-40]",
                         "num_designs": 1, "diffuser_T": 20}))
