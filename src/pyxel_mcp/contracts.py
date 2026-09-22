"""Typed public contracts for pyxel-mcp tools."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
AxisValue = Annotated[float, Field(ge=-1, le=1)]


class _InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InputEvent(_InputModel):
    frame: NonNegativeInt
    buttons: list[NonEmptyStr] | None = None
    axes: dict[str, AxisValue] | None = None
    mouse_pos: tuple[int, int] | None = None


SnapshotFrame = NonNegativeInt | Literal["end"]
SnapshotFrames = list[NonNegativeInt] | NonEmptyStr


class _TimedSnapshot(_InputModel):
    frame: SnapshotFrame | None = None
    frames: SnapshotFrames | None = None

    @model_validator(mode="after")
    def _one_frame_selector(self):
        if (self.frame is None) == (self.frames is None):
            raise ValueError("set exactly one of `frame` or `frames`")
        return self


class StateSnapshotRequest(_TimedSnapshot):
    kind: Literal["state"]
    attrs: list[NonEmptyStr] | None = None


class ScreenGridSnapshotRequest(_TimedSnapshot):
    kind: Literal["screen_grid"]
    bbox: tuple[NonNegativeInt, NonNegativeInt, PositiveInt, PositiveInt] | None = None


class ScreenImageSnapshotRequest(_TimedSnapshot):
    kind: Literal["screen_image"]
    output: NonEmptyStr | None = None
    output_pattern: NonEmptyStr | None = None
    scale: PositiveInt = 1
    inline: bool = Field(
        default=False,
        strict=True,
        description=(
            "Also return the captured PNG as image content. A single inline frame "
            "may omit `output`; the PNG then lands under the system temp directory "
            "and its path is still reported."
        ),
    )

    @model_validator(mode="after")
    def _matching_output(self):
        if self.output is not None and self.output_pattern is not None:
            raise ValueError("set only one of `output` or `output_pattern`")
        if self.frame is not None and self.output_pattern is not None:
            raise ValueError(
                "single-frame screen_image uses `output`, not `output_pattern`"
            )
        if self.frames is not None and self.output is not None:
            raise ValueError(
                "multi-frame screen_image uses `output_pattern`, not `output`"
            )
        selected = self.output or self.output_pattern
        if selected is None and not (self.inline and self.frame is not None):
            raise ValueError(
                "screen_image requires `output`, or `output_pattern` for several "
                "frames; only a single inline frame may omit it"
            )
        if selected and not selected.endswith(".png"):
            raise ValueError("screen_image output must end with `.png`")
        return self


class VideoSnapshotRequest(_InputModel):
    kind: Literal["video"]
    start_frame: NonNegativeInt
    end_frame: PositiveInt
    fps: PositiveInt = 30
    output: NonEmptyStr
    scale: PositiveInt = 1

    @model_validator(mode="after")
    def _ordered_frames(self):
        if self.start_frame >= self.end_frame:
            raise ValueError("`start_frame` must be less than `end_frame`")
        return self


SnapshotRequest = Annotated[
    StateSnapshotRequest
    | ScreenGridSnapshotRequest
    | ScreenImageSnapshotRequest
    | VideoSnapshotRequest,
    Field(discriminator="kind"),
]


class RunRequest(_InputModel):
    """Subprocess payload using the public scalar, input, and snapshot contracts."""

    script: NonEmptyStr
    frames: PositiveInt
    inputs: list[InputEvent] = Field(default_factory=list)
    snapshots: list[SnapshotRequest] = Field(default_factory=list)
    random_seed: NonNegativeInt | None = None
    timeout: PositiveInt = 10
    stall_window_frames: PositiveInt | None = None
    until: NonEmptyStr | None = None


class AudioTarget(_InputModel):
    sound: int | None = Field(default=None, ge=0)
    music: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _one_target(self):
        if (self.sound is None) == (self.music is None):
            raise ValueError("set exactly one of `sound` or `music`")
        return self


class ToolErrorRecord(_ResultModel):
    phase: str
    message: str
    path: str | None = None
    frame: int | None = None
    traceback: str | None = None


class Region(_ResultModel):
    x: int
    y: int
    w: int
    h: int


class ObservationResult(_ResultModel):
    ok: bool
    errors: list[ToolErrorRecord]


class StateSnapshotResult(_ResultModel):
    kind: Literal["state"]
    frame: int
    values: dict[str, JsonValue]
    warnings: list[str]


class ScreenGridSnapshotResult(_ResultModel):
    kind: Literal["screen_grid"]
    frame: int
    region: Region
    grid: list[list[int]]
    warnings: list[str]


class ScreenImageSnapshotResult(_ResultModel):
    kind: Literal["screen_image"]
    frame: int
    path: str
    size: tuple[int, int]
    inline: bool = False


class VideoSnapshotResult(_ResultModel):
    kind: Literal["video"]
    path: str
    format: Literal["gif", "mp4"]
    frames_encoded: int
    duration_seconds: float
    warnings: list[str]


SnapshotResult = Annotated[
    StateSnapshotResult
    | ScreenGridSnapshotResult
    | ScreenImageSnapshotResult
    | VideoSnapshotResult,
    Field(discriminator="kind"),
]


class RunResult(ObservationResult):
    snapshots: list[SnapshotResult]
    exit_status: Literal["ok", "crashed", "timeout", "stalled", "invalid"] = Field(
        description=(
            "ok includes reaching the frame budget, matching until, or an explicit "
            "pyxel.quit(). Cleanup failures are reported as crashed."
        )
    )
    frame_count: int = Field(
        description="Number of completed update/draw pairs; excludes a partial quit frame."
    )
    elapsed_seconds: float
    log: str
    seeded: bool
    until_met: bool | None = Field(
        default=None,
        description=(
            "True once `until` held, False when it was evaluated without ever "
            "holding, None when it was never evaluated."
        ),
    )


class ValidationIssue(_ResultModel):
    severity: Literal["error", "warning", "info"]
    line: int
    col: int | None
    category: str
    message: str


class ValidateResult(ObservationResult):
    issues: list[ValidationIssue] = Field(default_factory=list)


class ExampleInfo(_ResultModel):
    name: str
    path: str
    description: str | None = None


class PyxelInfoResult(ObservationResult):
    pyxel_mcp_version: str | None = None
    pyxel_version: str | None = None
    python_version: str | None = None
    stubs_path: str | None = None
    examples: list[ExampleInfo] = Field(default_factory=list)
    resources: dict[str, str] = Field(default_factory=dict)


class PaletteResult(ObservationResult):
    colors: dict[int, str] = Field(default_factory=dict)
    extended_palette: bool | None = None
    palette_size: int | None = None
    used_indices: list[int] = Field(default_factory=list)


class ImageResult(ObservationResult):
    image_index: int | None = None
    bank_size: tuple[int, int] | None = None
    region: Region | None = None
    pixels: list[list[int]] | None = None
    color_count: dict[int, int] = Field(default_factory=dict)
    rendered: str | None = None


class TilemapResult(ObservationResult):
    tilemap_index: int | None = None
    size: tuple[int, int] | None = None
    imgsrc: int | None = None
    tiles: list[list[list[int]]] | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    region: Region | None = None
    zero_tile_used: bool | None = None
    zero_tile_nonempty: bool | None = None
    rendered: str | None = None


class AudioNote(_ResultModel):
    frame: int
    note: str
    tone: str
    volume: int
    effect: str


class AudioResult(ObservationResult):
    path: str | None = None
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    peak_amplitude: float | None = None
    notes: list[AudioNote] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiffFramesResult(ObservationResult):
    identical: bool | None = None
    size_match: bool | None = None
    size_a: tuple[int, int] | None = None
    size_b: tuple[int, int] | None = None
    changed_pixels: int | None = None
    total_pixels: int | None = None
    ratio: float | None = None
    region: Region | None = None
    warnings: list[str] = Field(default_factory=list)
