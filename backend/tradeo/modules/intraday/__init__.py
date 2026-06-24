"""Intraday lane: shadow/paper validation, Director metadata and audit reports."""

from tradeo.modules.intraday.research_contracts import (
    INTRADAY_RESEARCH_CORE_VERSION,
    IntradayResearchDataContract,
    IntradayResearchDataContractBuilder,
)
from tradeo.modules.intraday.research_features import (
    IntradayFeatureCube,
    IntradayFeatureCubeBuilder,
    MultiScaleIntradaySample,
    MultiScaleIntradaySampler,
    MultiScaleSamplerConfig,
)
from tradeo.modules.intraday.research_validation_stack import (
    IntradayMatchedBaseline,
    IntradayMatchedBaselineFactory,
    IntradayValidationResult,
    IntradayValidationStack,
    IntradayValidationThresholds,
)

__all__ = [
    "INTRADAY_RESEARCH_CORE_VERSION",
    "IntradayFeatureCube",
    "IntradayFeatureCubeBuilder",
    "IntradayMatchedBaseline",
    "IntradayMatchedBaselineFactory",
    "IntradayResearchDataContract",
    "IntradayResearchDataContractBuilder",
    "IntradayValidationResult",
    "IntradayValidationStack",
    "IntradayValidationThresholds",
    "MultiScaleIntradaySample",
    "MultiScaleIntradaySampler",
    "MultiScaleSamplerConfig",
]
