"""Shared score scales for deduplication analysis and similarity banding."""

from enum import IntEnum


class VariationScoreScale(IntEnum):
    """Discrete variation complexity score levels used in pattern analysis."""

    SCORE_3 = 3
    SCORE_4 = 4
    SCORE_5 = 5
    SCORE_6 = 6
    SCORE_7 = 7


class VariationScoreCutoff(IntEnum):
    """Cutoff thresholds for mapping variation scores to complexity labels."""

    MODERATE_MAX = 4


class SimilarityDiscreteBand(IntEnum):
    """Discrete structural line-count bands for similarity bucketing."""

    BAND_3 = 3
    BAND_4 = 4
    BAND_5 = 5
    BAND_6 = 6
