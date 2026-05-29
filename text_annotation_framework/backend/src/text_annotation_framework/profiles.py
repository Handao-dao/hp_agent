from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationProfile:
    """一个 profile 描述“要提取什么、允许哪些类型、如何解释结果”。"""

    key: str
    label: str
    annotation_types: tuple[str, ...]
    instructions: str


class ProfileRegistry:
    """集中管理可用场景，避免 engine 直接写死某个业务 profile。"""

    def __init__(self, profiles: list[AnnotationProfile]):
        self._profiles = {profile.key: profile for profile in profiles}

    def get(self, key: str) -> AnnotationProfile:
        if key not in self._profiles:
            raise KeyError(f"Unknown annotation profile: {key}")
        return self._profiles[key]

    def get_or_default(
        self,
        key: str | None,
        default: str = "english_reading",
    ) -> AnnotationProfile:
        if key in self._profiles:
            return self._profiles[key]
        return self.get(default)

    def list_profiles(self) -> list[AnnotationProfile]:
        return list(self._profiles.values())

    def keys(self) -> list[str]:
        return list(self._profiles.keys())


def default_profile_registry() -> ProfileRegistry:
    """框架内置的最小 profile 集合；应用层可以替换或扩展这个 registry。"""

    return ProfileRegistry(
        [
            AnnotationProfile(
                key="english_reading",
                label="English Reading",
                annotation_types=("keyword", "phrase", "term"),
                instructions=(
                    "Find English words or phrases that are useful reading obstacles for a "
                    "learner. "
                    "Prefer concise Chinese labels. Focus on context-dependent meanings, idioms, "
                    "phrases, uncommon words, and terms that affect comprehension."
                ),
            ),
            AnnotationProfile(
                key="technical_terms",
                label="Technical Terms",
                annotation_types=("term", "concept", "phrase"),
                instructions=(
                    "Find technical terms, API names, configuration concepts, error concepts, "
                    "architecture terms, and domain-specific phrases. Keep labels concise "
                    "and precise."
                ),
            ),
            AnnotationProfile(
                key="general_keywords",
                label="General Keywords",
                annotation_types=("keyword", "entity", "concept"),
                instructions=(
                    "Find important keywords, entities, and concepts that summarize the text "
                    "or help "
                    "a reader navigate its meaning. Use neutral, compact labels."
                ),
            ),
        ]
    )
