from app.calibration.sequence import CalibrationProgress, CalibrationStage, STAGES


def test_colour_and_surface_precede_perception_and_geometry():
    assert STAGES.index(CalibrationStage.BLACK) < STAGES.index(CalibrationStage.PERCEPTION)
    assert STAGES.index(CalibrationStage.WHITE) < STAGES.index(CalibrationStage.PERCEPTION)
    assert STAGES.index(CalibrationStage.COLOUR) < STAGES.index(CalibrationStage.GEOMETRY)
    assert STAGES.index(CalibrationStage.SURFACE) < STAGES.index(CalibrationStage.GEOMETRY)
    assert STAGES[-1] == CalibrationStage.SAVE


def test_reprojection_starts_pending():
    progress = CalibrationProgress(stage=CalibrationStage.REPROJECTION)
    assert progress.reprojection_error is None
    progress = progress.set_reprojection_error(2.5)
    assert progress.reprojection_error == 2.5
